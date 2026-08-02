import ipaddress
import time
from urllib.parse import urlparse

import requests
from openai import OpenAI

from app.ai.config import AIConfig
from app.ai.logging_config import logger


class LLMClient:
    def __init__(self):
        self.provider = AIConfig.PROVIDER
        self.client = OpenAI(api_key=AIConfig.OPENAI_API_KEY, timeout=AIConfig.OPENAI_TIMEOUT) if AIConfig.OPENAI_API_KEY else None
        self._ollama_cache = None
        self._ollama_cache_at = 0.0

    @staticmethod
    def _timeout(timeout):
        """Separa conexão curta e tempo de resposta configurável."""
        if isinstance(timeout, tuple):
            return timeout
        return (AIConfig.OLLAMA_CONNECT_TIMEOUT, int(timeout or AIConfig.OLLAMA_TIMEOUT))

    @property
    def _openai_autorizada(self):
        return self.client is not None and AIConfig.OPENAI_DATA_CONSENT

    @property
    def _ollama_local(self):
        host = (urlparse(AIConfig.OLLAMA_URL).hostname or "").lower()
        if host == "localhost":
            return True
        try:
            return ipaddress.ip_address(host).is_loopback
        except ValueError:
            return False

    @property
    def _ollama_autorizado(self):
        return self._ollama_local or AIConfig.OLLAMA_EXTERNAL_CONSENT

    def _ollama_disponivel(self):
        if not self._ollama_autorizado:
            logger.info("Ollama externo não utilizado: consentimento para dados externos não concedido")
            return False
        cached = getattr(self, "_ollama_cache", None)
        checked_at = getattr(self, "_ollama_cache_at", 0.0)
        if cached is not None and time.monotonic() - checked_at < 10:
            return cached
        try:
            resposta = requests.get(f"{AIConfig.OLLAMA_URL.rstrip('/')}/api/tags", timeout=AIConfig.OLLAMA_CONNECT_TIMEOUT)
            resposta.raise_for_status()
            self._ollama_cache = True
            self._ollama_cache_at = time.monotonic()
            return True
        except requests.RequestException as erro:
            self._ollama_cache = False
            self._ollama_cache_at = time.monotonic()
            logger.info("Ollama indisponível: %s", erro)
            return False

    @staticmethod
    def _compact_prompt(prompt):
        limit = max(4000, int(AIConfig.OLLAMA_MAX_PROMPT_CHARS))
        if len(prompt) <= limit:
            return prompt
        tail_size = min(5000, limit // 3)
        head_size = limit - tail_size
        return (
            prompt[:head_size]
            + "\n\n[CONTEÚDO INTERMEDIÁRIO REDUZIDO POR LIMITE DE CONTEXTO]\n\n"
            + prompt[-tail_size:]
        )

    def disponivel(self):
        return (self.provider in ("auto", "ollama") and self._ollama_disponivel()) or (self.provider in ("auto", "openai") and self._openai_autorizada)

    def perguntar(self, prompt, json_mode=True, timeout=None):
        if self.provider in ("auto", "ollama") and self._ollama_disponivel():
            try:
                payload = {
                    "model": AIConfig.OLLAMA_MODEL,
                    "prompt": self._compact_prompt(prompt),
                    "stream": False,
                }
                if json_mode:
                    payload["format"] = "json"
                resposta = requests.post(
                    f"{AIConfig.OLLAMA_URL.rstrip('/')}/api/generate",
                    json=payload,
                    timeout=self._timeout(timeout),
                )
                resposta.raise_for_status()
                return resposta.json().get("response", "")
            except requests.RequestException as erro:
                self._ollama_cache = False
                self._ollama_cache_at = time.monotonic()
                logger.warning("Falha no Ollama: %s", erro)
                if self.provider == "ollama":
                    raise RuntimeError(f"Falha no Ollama: {erro}") from erro
        if self._openai_autorizada and self.provider in ("auto", "openai"):
            assert self.client is not None
            resposta = self.client.chat.completions.create(
                model=AIConfig.OPENAI_MODEL,
                temperature=0.2,
                timeout=timeout or AIConfig.OPENAI_TIMEOUT,
                messages=[{"role": "system", "content": "Você é especialista em RH e carreira."}, {"role": "user", "content": prompt}],
            )
            return resposta.choices[0].message.content or ""
        if self.client is not None and self.provider in ("auto", "openai"):
            logger.info("OpenAI não utilizada: consentimento para dados externos não concedido")
            raise RuntimeError("O uso da OpenAI requer autorização em Configurações > Privacidade OpenAI.")
        if self.provider == "ollama" and not self._ollama_autorizado:
            raise RuntimeError("Ollama remoto requer autorização em Configurações > Privacidade Ollama.")
        raise RuntimeError("Nenhum provedor de IA disponível.")

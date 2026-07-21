import requests
from openai import OpenAI

from app.ai.config import AIConfig
from app.ai.logging_config import logger


class LLMClient:
    def __init__(self):
        self.provider = AIConfig.PROVIDER
        self.client = OpenAI(api_key=AIConfig.OPENAI_API_KEY, timeout=AIConfig.OPENAI_TIMEOUT) if AIConfig.OPENAI_API_KEY else None

    @staticmethod
    def _timeout(timeout):
        """Separa conexão curta e tempo de resposta configurável."""
        if isinstance(timeout, tuple):
            return timeout
        return (AIConfig.OLLAMA_CONNECT_TIMEOUT, int(timeout or AIConfig.OLLAMA_TIMEOUT))

    @property
    def _openai_autorizada(self):
        return self.client is not None and AIConfig.OPENAI_DATA_CONSENT

    def _ollama_disponivel(self):
        try:
            resposta = requests.get(f"{AIConfig.OLLAMA_URL.rstrip('/')}/api/tags", timeout=AIConfig.OLLAMA_CONNECT_TIMEOUT)
            resposta.raise_for_status()
            return True
        except requests.RequestException as erro:
            logger.info("Ollama indisponível: %s", erro)
            return False

    def disponivel(self):
        return (self.provider in ("auto", "ollama") and self._ollama_disponivel()) or (self.provider in ("auto", "openai") and self._openai_autorizada)

    def perguntar(self, prompt, json_mode=True, timeout=None):
        if self.provider in ("auto", "ollama") and self._ollama_disponivel():
            try:
                payload = {"model": AIConfig.OLLAMA_MODEL, "prompt": prompt[:12000], "stream": False}
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
                logger.warning("Falha no Ollama: %s", erro)
                if self.provider == "ollama":
                    raise RuntimeError(f"Falha no Ollama: {erro}") from erro
        if self._openai_autorizada and self.provider in ("auto", "openai"):
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
        raise RuntimeError("Nenhum provedor de IA disponível.")

import requests
from openai import OpenAI

from app.ai.config import AIConfig
from app.ai.logging_config import logger


class LLMClient:
    def __init__(self):
        self.provider = AIConfig.PROVIDER
        self.client = OpenAI(api_key=AIConfig.OPENAI_API_KEY) if AIConfig.OPENAI_API_KEY else None

    def _ollama_disponivel(self):
        try:
            resposta = requests.get(f"{AIConfig.OLLAMA_URL.rstrip('/')}/api/tags", timeout=AIConfig.OLLAMA_CONNECT_TIMEOUT)
            resposta.raise_for_status()
            return True
        except requests.RequestException as erro:
            logger.info("Ollama indisponível: %s", erro)
            return False

    def disponivel(self):
        return (self.provider in ("auto", "ollama") and self._ollama_disponivel()) or (self.provider in ("auto", "openai") and self.client is not None)

    def perguntar(self, prompt, json_mode=True, timeout=None):
        if self.provider in ("auto", "ollama") and self._ollama_disponivel():
            try:
                payload = {"model": AIConfig.OLLAMA_MODEL, "prompt": prompt[:12000], "stream": False}
                if json_mode:
                    payload["format"] = "json"
                resposta = requests.post(
                    f"{AIConfig.OLLAMA_URL.rstrip('/')}/api/generate",
                    json=payload,
                    timeout=timeout or AIConfig.OLLAMA_TIMEOUT,
                )
                resposta.raise_for_status()
                return resposta.json().get("response", "")
            except requests.RequestException as erro:
                logger.warning("Falha no Ollama: %s", erro)
                if self.provider == "ollama":
                    raise RuntimeError(f"Falha no Ollama: {erro}") from erro
        if self.client is not None and self.provider in ("auto", "openai"):
            resposta = self.client.chat.completions.create(model=AIConfig.OPENAI_MODEL, temperature=0.2, messages=[{"role": "system", "content": "Você é especialista em RH e carreira."}, {"role": "user", "content": prompt}])
            return resposta.choices[0].message.content or ""
        raise RuntimeError("Nenhum provedor de IA disponível.")

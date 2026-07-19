import requests
from openai import OpenAI

from app.ai.config import AIConfig


class LLMClient:

    def __init__(self):
        self.provider = AIConfig.PROVIDER
        self.client = None

        if (
            self.provider == "openai"
            and AIConfig.OPENAI_API_KEY
        ):
            self.client = OpenAI(
                api_key=AIConfig.OPENAI_API_KEY
            )

    def disponivel(self):

        if self.provider == "ollama":
            try:
                requests.get(
                    AIConfig.OLLAMA_URL + "/api/tags",
                    timeout=5
                ).raise_for_status()
                return True
            except Exception as e:
                print("ERRO AO CONECTAR AO OLLAMA:", e)
                return False

        return self.client is not None

    def perguntar(self, prompt):

        if self.provider == "ollama":

            prompt_final = (
                "Você é um especialista em RH, recrutamento, ATS e análise de currículos.\n\n"
                + prompt[:12000]
            )

            print("=" * 80)
            print("USANDO OLLAMA")
            print("MODELO:", AIConfig.OLLAMA_MODEL)
            print("TAMANHO DO PROMPT:", len(prompt_final))
            print("=" * 80)

            resposta = requests.post(
                AIConfig.OLLAMA_URL + "/api/generate",
                json={
                    "model": AIConfig.OLLAMA_MODEL,
                    "prompt": prompt_final,
                    "stream": False,
                    "format": "json"
                },
                timeout=300
            )

            resposta.raise_for_status()

            dados = resposta.json()

            conteudo = dados.get("response", "")

        else:

            resposta = self.client.chat.completions.create(
                model=AIConfig.OPENAI_MODEL,
                temperature=0.2,
                messages=[
                    {
                        "role": "system",
                        "content": "Você é especialista em RH, recrutamento e análise de currículos."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            conteudo = resposta.choices[0].message.content

        print("=" * 80)
        print("RESPOSTA DA IA")
        print("=" * 80)
        print(conteudo)
        print("=" * 80)

        return conteudo

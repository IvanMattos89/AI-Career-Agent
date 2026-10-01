import unittest

from app.services.career_assistant_service import CareerAssistantService


class _Db:
    def listar_confirmacoes_competencias(self, _resume_id):
        return {}

    def obter_analise_ativa(self):
        return {
            "resume_id": 1, "cargo": "Analista Fiscal", "area": "Fiscal", "senioridade": "Pleno",
            "hard_skills": "Excel; ICMS", "pontos_melhoria": "", "competencias_faltantes": "", "resumo": "",
        }

    def obter_curriculo(self, _resume_id):
        return {"texto": "Apuração de ICMS."}

    def salvar_mensagem_assistente(self, *_args):
        pass

    def salvar_entrevista(self, *_args):
        return 1


class _UnstableLlm:
    def disponivel(self):
        return True

    def perguntar(self, *_args, **_kwargs):
        raise RuntimeError("Nenhum provedor de IA disponível.")


class CareerOfflineFallbackTest(unittest.TestCase):
    def setUp(self):
        self.service = CareerAssistantService.__new__(CareerAssistantService)
        self.service.db = _Db()
        self.service.llm = _UnstableLlm()

    def test_chat_falls_back_when_provider_drops(self):
        resposta = self.service.conversar("Como me preparar?")
        self.assertIn("modo local", resposta)

    def test_interview_question_falls_back_when_provider_drops(self):
        pergunta = self.service.proxima_pergunta("RH")
        self.assertTrue(pergunta.endswith("?"))

    def test_feedback_falls_back_when_provider_drops(self):
        resultado = self.service.avaliar_resposta("Pergunta", "Minha resposta possui detalhes suficientes para avaliação.", "RH")
        self.assertIsNone(resultado["nota"])
        self.assertIn("modo local", resultado["feedback"])

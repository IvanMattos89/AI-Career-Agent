import unittest

from app.services.job_match_service import JobMatchService


class _FakeDb:
    def __init__(self):
        self.saved = None

    def obter_ultima_analise(self):
        return {
            "resume_id": 7, "nome_arquivo": "curriculo.docx", "cargo": "Analista Fiscal",
            "area": "Fiscal", "senioridade": "Pleno", "hard_skills": "Excel; ICMS",
            "soft_skills": "", "tecnologias": "ERP", "idiomas": "", "certificacoes": "", "resumo": "",
        }

    def salvar_job_match(self, resume_id, descricao, resultado, titulo=None):
        self.saved = (resume_id, descricao, resultado, titulo)
        return 99


class _FailingLlm:
    def disponivel(self):
        return True


class _FailingAnalyzer:
    llm = _FailingLlm()

    def comparar(self, _prompt):
        raise RuntimeError("timeout simulado")


class JobMatchFallbackTest(unittest.TestCase):
    def test_uses_local_result_when_ai_fails_after_health_check(self):
        service = JobMatchService.__new__(JobMatchService)
        service.db = _FakeDb()
        service.analyzer = _FailingAnalyzer()

        result = service.comparar("A vaga exige Excel, ICMS e ERP.", "Analista Fiscal")

        self.assertEqual(result["id"], 99)
        self.assertGreater(result["compatibilidade"], 0)
        self.assertIn("Excel", result["competencias_encontradas"])

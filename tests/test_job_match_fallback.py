import json
import unittest

from app.services.job_match_service import JobMatchService


class _FakeDb:
    def __init__(self):
        self.saved = None

    def obter_analise_ativa(self):
        return {
            "resume_id": 7, "nome_arquivo": "curriculo.docx", "cargo": "Analista Fiscal",
            "area": "Fiscal", "senioridade": "Pleno", "hard_skills": "Excel; ICMS",
            "soft_skills": "", "tecnologias": "ERP", "idiomas": "", "certificacoes": "", "resumo": "",
        }

    def salvar_job_match(self, resume_id, descricao, resultado, titulo=None):
        self.saved = (resume_id, descricao, resultado, titulo)
        return 99

    def obter_curriculo(self, _resume_id):
        return {"texto": "Empresa X — Analista Fiscal — apuração de ICMS em SAP."}


class _FailingLlm:
    def disponivel(self):
        return True


class _FailingAnalyzer:
    llm = _FailingLlm()

    def comparar(self, _prompt):
        raise RuntimeError("timeout simulado")


class _CapturingAnalyzer:
    llm = _FailingLlm()

    def __init__(self):
        self.prompt = ""

    def comparar(self, prompt, timeout=None):
        self.prompt = prompt
        return json.dumps({
            "compatibilidade": 80,
            "competencias_encontradas": ["ICMS"],
            "competencias_faltantes": [],
            "recomendacoes": [],
            "explicacao": "Evidência profissional localizada.",
            "resumo": "Compatível.",
        })


class JobMatchFallbackTest(unittest.TestCase):
    def test_uses_local_result_when_ai_fails_after_health_check(self):
        service = JobMatchService.__new__(JobMatchService)
        service.db = _FakeDb()
        service.analyzer = _FailingAnalyzer()

        result = service.comparar("A vaga exige Excel, ICMS e ERP.", "Analista Fiscal")

        self.assertEqual(result["id"], 99)
        self.assertGreater(result["compatibilidade"], 0)
        self.assertIn("Excel", result["competencias_encontradas"])

    def test_sends_full_career_evidence_to_ai_comparison(self):
        service = JobMatchService.__new__(JobMatchService)
        service.db = _FakeDb()
        service.analyzer = _CapturingAnalyzer()

        service.comparar("Vaga exige ICMS em SAP.", "Analista Fiscal")

        self.assertIn("Empresa X", service.analyzer.prompt)
        self.assertIn("apuração de ICMS em SAP", service.analyzer.prompt)
        self.assertIn("Diferencie experiência profissional", service.analyzer.prompt)

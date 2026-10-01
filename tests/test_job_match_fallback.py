import json
import unittest

from app.services.job_match_service import JobMatchService


class _FakeDb:
    def listar_confirmacoes_competencias(self, _resume_id):
        return {}

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

    def __init__(self):
        self.calls = []

    def comparar(self, prompt, timeout=None):
        self.calls.append((prompt, timeout))
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
        self.assertIsNone(result["compatibilidade"])
        self.assertIn("Excel", result["competencias_nao_informadas"])
        self.assertEqual(len(service.analyzer.calls), 1)
        self.assertEqual(service.analyzer.calls[0][1], 20)
        self.assertIn("A vaga exige Excel", service.analyzer.calls[0][0])

    def test_sends_full_career_evidence_to_ai_comparison(self):
        service = JobMatchService.__new__(JobMatchService)
        service.db = _FakeDb()
        service.analyzer = _CapturingAnalyzer()

        service.comparar("Vaga exige ICMS em SAP.", "Analista Fiscal")

        self.assertIn("Empresa X", service.analyzer.prompt)
        self.assertIn("apuração de ICMS em SAP", service.analyzer.prompt)
        self.assertIn("Diferencie experiência profissional", service.analyzer.prompt)

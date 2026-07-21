import unittest

from app.services.resume_adaptation_service import ResumeAdaptationService


class _Db:
    def obter_ultima_analise(self):
        return {
            "resume_id": 1, "nome_arquivo": "curriculo.docx", "cargo": "Analista Fiscal",
            "area": "Fiscal e Tributária", "hard_skills": "Excel; ICMS; SPED", "tecnologias": "ERP; Excel",
        }

    def obter_curriculo(self, _resume_id):
        return {"texto": "Experiência com ICMS, SPED e ERP."}


class ResumeAdaptationServiceTest(unittest.TestCase):
    def test_prepares_reviewable_resume_without_changing_original(self):
        service = ResumeAdaptationService.__new__(ResumeAdaptationService)
        service.db = _Db()

        resultado = service.preparar("Vaga exige Excel, ICMS e SPED.", "Analista Fiscal")

        self.assertEqual(resultado["vaga"], "Analista Fiscal")
        self.assertIn("ICMS", resultado["competencias_alinhadas"])
        self.assertEqual(resultado["texto_original"], "Experiência com ICMS, SPED e ERP.")

import unittest

from app.ai.analyzer import ResumeAnalyzer
from app.ai.skill_detector import SkillDetector


class LocalAnalysisTest(unittest.TestCase):
    def test_identifies_fiscal_profile_without_external_ai(self):
        analyzer = ResumeAnalyzer.__new__(ResumeAnalyzer)
        analyzer.skill_detector = SkillDetector()

        resultado = analyzer._analise_local(
            "Analista Fiscal com mais de 10 anos de experiência em ICMS, SPED e SAP. "
            "CRC ativo. Inglês avançado."
        )

        self.assertEqual(resultado.cargo, "Analista Fiscal")
        self.assertEqual(resultado.senioridade, "Sênior")
        self.assertEqual(resultado.anos_experiencia, 10)
        self.assertIn("ICMS", resultado.hard_skills)
        self.assertIn("Inglês", resultado.idiomas)
        self.assertIn("CRC", resultado.certificacoes)

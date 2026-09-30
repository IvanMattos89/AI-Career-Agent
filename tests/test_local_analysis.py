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

    def test_word_boundaries_do_not_match_substrings(self):
        analyzer = ResumeAnalyzer.__new__(ResumeAnalyzer)
        analyzer.skill_detector = SkillDetector()

        self.assertEqual(analyzer._detectar_idiomas("curso de ingleses"), [])

    def test_skill_detector_does_not_match_substrings_or_nested_language(self):
        detector = SkillDetector()

        self.assertEqual(detector.detectar("Missão digital com piso elevado."), [])
        self.assertEqual(detector.detectar("JavaScript"), ["JavaScript"])

    def test_sap_is_not_a_certification_without_certification_context(self):
        analyzer = ResumeAnalyzer.__new__(ResumeAnalyzer)

        self.assertNotIn("Certificação SAP", analyzer._detectar_certificacoes("experiencia em sap"))
        self.assertNotIn(
            "Certificação SAP",
            analyzer._detectar_certificacoes("academia sap s 4hana concluida"),
        )

    def test_calculates_experience_from_non_overlapping_periods(self):
        analyzer = ResumeAnalyzer.__new__(ResumeAnalyzer)

        years = analyzer._anos_experiencia(
            "01/2015 - 12/2019 Empresa A 01/2020 - 12/2024 Empresa B"
        )

        self.assertEqual(years, 10)

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.ui.pages.analysis_page import AnalysisPage


class AnalysisPageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_loads_saved_analysis_when_resume_exists(self):
        page = AnalysisPage()
        page.db = type("Db", (), {"obter_ultima_analise": lambda _self: {
            "ats_score": 80, "cargo": "Analista Fiscal", "area": "Fiscal e Tributária",
            "senioridade": "Pleno", "anos_experiencia": 3, "hard_skills": "EFD; Excel",
            "soft_skills": "", "tecnologias": "ERP", "idiomas": "", "certificacoes": "",
            "palavras_chave": "SPED", "pontos_fortes": "", "pontos_melhoria": "",
            "competencias_faltantes": "", "recomendacoes": "", "resumo": "Resumo",
        }})()
        self.assertTrue(page.carregar_ultima_analise())
        self.assertEqual(page.cardCargo.lblValor.text(), "Analista Fiscal")
        self.assertEqual(page.score.lblScore.text(), "80")

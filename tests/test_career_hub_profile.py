import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.ui.pages.career_hub_page import CareerHubPage


class CareerHubProfileTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_active_resume_summary_uses_brazilian_recommendation(self):
        page = CareerHubPage()
        texto = page.perfil_resumo.text()
        if "Perfil ativo:" in texto:
            self.assertIn("Busca recomendada (Brasil):", texto)
            self.assertNotIn("Busca recomendada (Brasil):</b> tax accountant", texto)

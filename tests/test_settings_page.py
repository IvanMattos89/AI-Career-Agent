import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLineEdit

from app.ui.settings_page import SettingsPage


class FakeDatabase:
    def dashboard_total_curriculos(self):
        return 2

    def dashboard_job_match_metricas(self):
        return {"total": 4}

    def listar_oportunidades(self):
        return [1]

    def diagnostico(self):
        return {"integridade": "ok", "migracao": 2, "tamanho_bytes": 1024}

    def metricas_provedores(self):
        return []


class SettingsPageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_organizes_settings_and_keeps_secrets_hidden(self):
        with patch("app.ui.settings_page.Database", return_value=FakeDatabase()):
            page = SettingsPage()

        self.assertEqual(page.tabs.count(), 3)
        self.assertEqual(page.gupy_token.echoMode(), QLineEdit.Password)
        self.assertEqual(page.jooble_key.echoMode(), QLineEdit.Password)
        self.assertIn("fontes ativas", page.provider_summary.text())

    def test_validates_ollama_url_and_adzuna_pair(self):
        values = {
            "OLLAMA_MODEL": "model", "OPENAI_MODEL": "model", "OLLAMA_TIMEOUT": "60",
            "OLLAMA_URL": "invalid", "ADZUNA_APP_ID": "", "ADZUNA_APP_KEY": "",
        }
        self.assertIn("URL", SettingsPage._validar(values))
        values["OLLAMA_URL"] = "http://localhost:11434"
        values["ADZUNA_APP_ID"] = "id"
        self.assertIn("Adzuna", SettingsPage._validar(values))


if __name__ == "__main__":
    unittest.main()

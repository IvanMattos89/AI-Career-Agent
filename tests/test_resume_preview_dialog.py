import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.ui.resume_preview_dialog import ResumePreviewDialog


class _Reports:
    pass


class ResumePreviewDialogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_shows_editable_preview_and_evidence_matrix(self):
        dialog = ResumePreviewDialog({
            "texto_previa": "MARIA\nRESUMO PROFISSIONAL\nTexto revisável",
            "matriz_evidencias": [{
                "requisito": "ICMS", "prioridade": "Obrigatório",
                "status": "Comprovado", "evidencia": "Apuração de ICMS",
                "fonte": "Experiência profissional", "acao": "Destacar",
            }],
            "alertas": [],
        }, _Reports())

        self.assertFalse(dialog.editor.isReadOnly())
        self.assertEqual(dialog.evidence.rowCount(), 1)
        self.assertEqual(dialog.evidence.item(0, 2).text(), "Comprovado")


if __name__ == "__main__":
    unittest.main()

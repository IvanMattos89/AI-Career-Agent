import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from docx import Document

from app.services.resume_service import ResumeService


class ResumeServiceTest(unittest.TestCase):
    def test_imports_valid_docx_into_managed_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "curriculo.docx"
            managed = root / "managed"
            document = Document()
            document.add_paragraph("Analista Fiscal com 10 anos de experiência em ICMS e SPED.")
            document.save(source)
            with (
                patch("app.services.resume_service.RESUMES_DIR", managed),
                patch("app.database.sqlite_db.DATA_DIR", root),
                patch("app.database.sqlite_db.DATABASE", root / "career.db"),
                patch("app.database.sqlite_db.RESUMES_DIR", managed),
            ):
                service = ResumeService()
                result = service.importar(source)
                service.db.close()

            self.assertTrue(result.destination.is_file())
            self.assertIn("Analista Fiscal", result.text)

    def test_rejects_unsupported_extension(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "curriculo.txt"
            file.write_text("currículo", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Formato não suportado"):
                ResumeService.validar_arquivo(ResumeService.__new__(ResumeService), file)


if __name__ == "__main__":
    unittest.main()

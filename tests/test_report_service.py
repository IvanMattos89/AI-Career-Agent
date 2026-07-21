import tempfile
import unittest
from pathlib import Path

from docx import Document
from pypdf import PdfReader

from app.services.report_service import ReportService


class ReportServiceTest(unittest.TestCase):
    def setUp(self):
        self.dados = {
            "vaga": "Analista Fiscal",
            "resumo_direcionado": "Profissional com experiência fiscal e tributária.",
            "competencias_alinhadas": ["ICMS", "SPED", "Excel"],
            "palavras_revisar": [],
            "texto_original": (
                "Maria da Silva\n"
                "São Paulo/SP | maria@example.com\n"
                "OBJETIVO PROFISSIONAL\n"
                "ANALISTA FISCAL\n"
                "SÍNTESE DE QUALIFICAÇÕES\n"
                "Experiência em ICMS, SPED e obrigações acessórias."
            ),
        }

    def test_generates_readable_abnt_style_pdf(self):
        with tempfile.TemporaryDirectory() as pasta:
            destino = Path(pasta) / "curriculo.pdf"
            ReportService().exportar_curriculo_adaptado_pdf(self.dados, destino)

            self.assertTrue(destino.exists())
            texto = "\n".join(pagina.extract_text() or "" for pagina in PdfReader(destino).pages)
            self.assertIn("MARIA DA SILVA", texto)
            self.assertIn("OBJETIVO PROFISSIONAL", texto)
            self.assertIn("experiência fiscal", texto.lower())

    def test_generates_docx_with_formal_margins(self):
        with tempfile.TemporaryDirectory() as pasta:
            service = ReportService()
            service.output_dir = Path(pasta)
            destino = service.exportar_curriculo_adaptado_docx(self.dados)
            documento = Document(destino)

            self.assertEqual(round(documento.sections[0].top_margin.cm), 3)
            self.assertEqual(round(documento.sections[0].left_margin.cm), 3)
            self.assertEqual(round(documento.sections[0].right_margin.cm), 2)
            self.assertIn("RESUMO PROFISSIONAL", [p.text for p in documento.paragraphs])

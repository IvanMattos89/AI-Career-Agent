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

    def test_generates_readable_ats_style_pdf(self):
        with tempfile.TemporaryDirectory() as pasta:
            destino = Path(pasta) / "curriculo.pdf"
            ReportService().exportar_curriculo_adaptado_pdf(self.dados, destino)

            self.assertTrue(destino.exists())
            texto = "\n".join(pagina.extract_text() or "" for pagina in PdfReader(destino).pages)
            self.assertIn("MARIA DA SILVA", texto)
            self.assertIn("OBJETIVO PROFISSIONAL", texto)
            self.assertIn("experiência fiscal", texto.lower())

    def test_generates_docx_with_compact_ats_margins(self):
        with tempfile.TemporaryDirectory() as pasta:
            service = ReportService()
            service.output_dir = Path(pasta)
            destino = service.exportar_curriculo_adaptado_docx(self.dados)
            documento = Document(destino)

            self.assertAlmostEqual(documento.sections[0].top_margin.cm, 1.85, places=1)
            self.assertAlmostEqual(documento.sections[0].left_margin.cm, 1.85, places=1)
            self.assertAlmostEqual(documento.sections[0].right_margin.cm, 1.85, places=1)
            self.assertIn("RESUMO PROFISSIONAL", [p.text for p in documento.paragraphs])

    def test_generates_job_match_pdf(self):
        with tempfile.TemporaryDirectory() as pasta:
            destino = Path(pasta) / "job_match.pdf"
            resultado = {
                "compatibilidade": 78,
                "explicacao": "Há aderência entre as competências e os requisitos.",
                "competencias_encontradas": ["ICMS", "Excel"],
                "competencias_faltantes": ["Power BI"],
                "recomendacoes": ["Inclua resultados mensuráveis."],
            }
            ReportService().exportar_job_match_pdf(resultado, destino)
            texto = "\n".join(pagina.extract_text() or "" for pagina in PdfReader(destino).pages)
            self.assertIn("RELATÓRIO DE JOB MATCH", texto)
            self.assertIn("78%", texto)

    def test_docx_and_pdf_share_all_alternative_sections(self):
        data = {
            "vaga": "Analista Fiscal",
            "titulo_direcionado": "Analista Fiscal | ICMS | SAP",
            "resumo_direcionado": "Resumo baseado em evidências.",
            "competencias_alinhadas": ["ICMS", "SAP"],
            "palavras_revisar": [],
            "texto_original": (
                "Maria da Silva\nContato\nPERFIL PROFISSIONAL\nResumo original\n"
                "EXPERIÊNCIAS PROFISSIONAIS\nEmpresa X | 2020 - Atual\n- Apuração de ICMS\n"
                "FORMAÇÃO\nCiências Contábeis\nSISTEMAS\nSAP\nIDIOMAS\nInglês"
            ),
        }
        with tempfile.TemporaryDirectory() as folder:
            service = ReportService()
            service.output_dir = Path(folder)
            docx_path = service.exportar_curriculo_adaptado_docx(data)
            pdf_path = Path(folder) / "curriculo.pdf"
            service.exportar_curriculo_adaptado_pdf(data, pdf_path)
            docx_text = "\n".join(paragraph.text for paragraph in Document(docx_path).paragraphs)
            pdf_text = "\n".join(page.extract_text() or "" for page in PdfReader(pdf_path).pages)

            for expected in (
                "Resumo original", "Empresa X", "Apuração de ICMS",
                "Ciências Contábeis", "SAP", "Inglês",
            ):
                self.assertIn(expected, docx_text)
                self.assertIn(expected, pdf_text)

    def test_experience_groups_company_role_period_and_activities(self):
        section = {
            "items": [
                {"text": "03/2025–Atual CPFL"},
                {"text": "(Empresa nacional de grande porte)"},
                {"text": "Analista Fiscal Sr."},
                {"text": "Apuração de ICMS e entrega de obrigações acessórias."},
            ]
        }

        groups = ReportService._experience_groups(section)

        self.assertEqual(groups[0]["company"], "CPFL")
        self.assertEqual(groups[0]["period"], "03/2025–Atual")
        self.assertEqual(groups[0]["role"], "Analista Fiscal Sr")
        self.assertEqual(groups[0]["description"], "(Empresa nacional de grande porte)")
        self.assertEqual(
            groups[0]["activities"],
            ["Apuração de ICMS e entrega de obrigações acessórias."],
        )

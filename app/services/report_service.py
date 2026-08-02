import re
from datetime import datetime
from pathlib import Path
from typing import Any

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer

from app.config import REPORTS_DIR
from app.services.resume_structure_service import ResumeStructureService


class ReportService:
    """Gera um relatório DOCX para um resultado de Job Match salvo ou recém-calculado."""

    ACCENT = "183B56"

    def __init__(self):
        self.output_dir = REPORTS_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _experience_groups(section):
        groups: list[dict[str, Any]] = []
        current: dict[str, Any] | None = None
        period_pattern = re.compile(
            r"^(?P<period>(?:\d{2}/\d{4}|\d{4})\s*[-–—]\s*"
            r"(?:atual|\d{2}/\d{4}|\d{4}))\s+(?P<company>.+)$",
            flags=re.I,
        )
        for item in section.get("items", []):
            match = period_pattern.match(item["text"].strip())
            if match:
                if current:
                    groups.append(current)
                current = {
                    "company": match.group("company").strip(),
                    "period": match.group("period").strip(),
                    "role": "", "description": "", "activities": [],
                }
                continue
            if current is None:
                current = {"company": "", "period": "", "role": "", "description": "", "activities": []}
            text = item["text"].strip()
            if not current["description"] and text.startswith("(") and text.endswith(")"):
                current["description"] = text
            elif not current["role"] and len(text) <= 100 and any(
                role in ResumeStructureService.normalize(text)
                for role in (
                    "analista", "consultor", "especialista", "coordenador", "gerente",
                    "contador", "assistente", "supervisor", "auditor", "manager",
                    "accountant", "consultant", "engineer",
                )
            ):
                current["role"] = text.rstrip(".")
            else:
                current["activities"].append(text)
        if current:
            groups.append(current)
        return groups

    @staticmethod
    def _register_pdf_fonts():
        """Usa Arial no Windows e mantém Helvetica como fallback portátil."""
        regular = Path("C:/Windows/Fonts/arial.ttf")
        bold = Path("C:/Windows/Fonts/arialbd.ttf")
        if regular.is_file() and bold.is_file():
            if "ArialResume" not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont("ArialResume", str(regular)))
                pdfmetrics.registerFont(TTFont("ArialResume-Bold", str(bold)))
            return "ArialResume", "ArialResume-Bold"
        return "Helvetica", "Helvetica-Bold"

    def exportar_job_match_docx(self, resultado):
        documento = Document()
        secao = documento.sections[0]
        secao.top_margin = secao.bottom_margin = Inches(0.75)
        estilos = documento.styles
        estilos["Normal"].font.name = "Aptos"
        estilos["Normal"].font.size = Pt(10.5)

        documento.add_heading("Relatório de Job Match", 0)
        documento.add_paragraph(f"Gerado em {datetime.now():%d/%m/%Y às %H:%M}")
        documento.add_paragraph(f"Currículo analisado: {resultado.get('curriculo', '-')}")
        documento.add_heading(f"Compatibilidade: {resultado.get('compatibilidade', 0)}%", 1)
        documento.add_paragraph(resultado.get("explicacao", ""))

        for titulo, chave in (
            ("Competências encontradas", "competencias_encontradas"),
            ("Competências a desenvolver", "competencias_faltantes"),
            ("Recomendações", "recomendacoes"),
        ):
            documento.add_heading(titulo, 1)
            itens = resultado.get(chave, [])
            if itens:
                for item in itens:
                    documento.add_paragraph(str(item), style="List Bullet")
            else:
                documento.add_paragraph("Nenhum item identificado.")

        documento.add_heading("Resumo", 1)
        documento.add_paragraph(resultado.get("resumo", "-"))
        destino = self.output_dir / f"job_match_{datetime.now():%Y%m%d_%H%M%S}.docx"
        documento.save(destino)
        return destino

    def exportar_job_match_pdf(self, resultado, destino):
        """Gera PDF legível em A4 sem depender das fontes instaladas no Windows."""
        documento = SimpleDocTemplate(
            str(destino), pagesize=A4,
            leftMargin=2.5 * cm, rightMargin=2.0 * cm,
            topMargin=2.5 * cm, bottomMargin=2.0 * cm,
            title="Relatório de Job Match",
        )
        estilos = getSampleStyleSheet()
        titulo = ParagraphStyle("TituloJobMatch", parent=estilos["Normal"], fontName="Helvetica-Bold", fontSize=16, leading=20, spaceAfter=12)
        secao = ParagraphStyle("SecaoJobMatch", parent=estilos["Normal"], fontName="Helvetica-Bold", fontSize=12, leading=15, spaceBefore=8, spaceAfter=4)
        corpo = ParagraphStyle("CorpoJobMatch", parent=estilos["Normal"], fontName="Helvetica", fontSize=10.5, leading=15, alignment=TA_JUSTIFY, spaceAfter=3)
        historia = [
            Paragraph("RELATÓRIO DE JOB MATCH", titulo),
            Paragraph(f"Compatibilidade: <b>{int(resultado.get('compatibilidade', 0))}%</b>", corpo),
            Paragraph("COMO A NOTA FOI CALCULADA", secao),
            Paragraph(self._escapar_pdf(resultado.get("explicacao", "-")), corpo),
        ]
        for cabecalho, chave in (
            ("COMPETÊNCIAS ENCONTRADAS", "competencias_encontradas"),
            ("COMPETÊNCIAS A DESENVOLVER", "competencias_faltantes"),
            ("RECOMENDAÇÕES", "recomendacoes"),
        ):
            historia.append(Paragraph(cabecalho, secao))
            itens = resultado.get(chave, []) or []
            if itens:
                historia.extend(Paragraph("• " + self._escapar_pdf(item), corpo) for item in itens)
            else:
                historia.append(Paragraph("Nenhum item identificado.", corpo))
        documento.build(historia)

    def exportar_pacote_candidatura_docx(self, pacote):
        documento = Document()
        secao = documento.sections[0]
        secao.top_margin = secao.bottom_margin = Inches(0.75)
        estilos = documento.styles
        estilos["Normal"].font.name = "Aptos"
        estilos["Normal"].font.size = Pt(10.5)
        documento.add_heading("Material de Candidatura", 0)
        documento.add_paragraph(f"Vaga: {pacote.get('vaga', '-')}")
        if pacote.get("empresa"):
            documento.add_paragraph(f"Empresa: {pacote['empresa']}")
        documento.add_heading("Carta de apresentação", 1)
        for paragrafo in pacote.get("carta", "").split("\n\n"):
            documento.add_paragraph(paragrafo)
        documento.add_heading("Resumo direcionado", 1)
        documento.add_paragraph(pacote.get("resumo_direcionado", ""))
        documento.add_heading("Palavras-chave para revisar", 1)
        for item in pacote.get("palavras_chave", []):
            documento.add_paragraph(item, style="List Bullet")
        documento.add_heading("Checklist antes de candidatar", 1)
        for item in pacote.get("checklist", []):
            documento.add_paragraph(item, style="List Bullet")
        destino = self.output_dir / f"candidatura_{datetime.now():%Y%m%d_%H%M%S}.docx"
        documento.save(destino)
        return destino

    def exportar_curriculo_adaptado_docx(self, dados, destino=None):
        """Gera currículo ATS compacto a partir da estrutura usada também pelo PDF."""
        documento = Document()
        secao = documento.sections[0]
        secao.page_width = Cm(21)
        secao.page_height = Cm(29.7)
        secao.top_margin = secao.bottom_margin = Cm(1.85)
        secao.left_margin = secao.right_margin = Cm(1.85)
        normal = documento.styles["Normal"]
        normal.font.name = "Arial"
        normal._element.rPr.rFonts.set(qn("w:ascii"), "Arial")
        normal._element.rPr.rFonts.set(qn("w:hAnsi"), "Arial")
        normal.font.size = Pt(10.5)
        normal.paragraph_format.space_after = Pt(1.5)
        normal.paragraph_format.line_spacing = 1.05
        heading = documento.styles.add_style("Resume Section", WD_STYLE_TYPE.PARAGRAPH)
        heading.font.name = "Arial"
        heading._element.rPr.rFonts.set(qn("w:ascii"), "Arial")
        heading._element.rPr.rFonts.set(qn("w:hAnsi"), "Arial")
        heading.font.size = Pt(13)
        heading.font.bold = True
        heading.font.color.rgb = RGBColor.from_string(self.ACCENT)
        heading.paragraph_format.space_before = Pt(7)
        heading.paragraph_format.space_after = Pt(3)
        heading.paragraph_format.keep_with_next = True
        bullet = documento.styles["List Bullet"]
        bullet.font.name = "Arial"
        bullet.font.size = Pt(10.5)
        bullet.paragraph_format.left_indent = Cm(0.5)
        bullet.paragraph_format.first_line_indent = Cm(-0.28)
        bullet.paragraph_format.space_after = Pt(1)
        bullet.paragraph_format.line_spacing = 1.02

        structure = self._resume_structure(dados)
        header = structure.get("header", [])
        if header:
            paragraph = documento.add_paragraph()
            paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
            paragraph.paragraph_format.space_after = Pt(2)
            run = paragraph.add_run(header[0].upper())
            run.bold = True
            run.font.name = "Arial"
            run.font.size = Pt(20)
            contact_start = 1
            if dados.get("titulo_direcionado") and len(header) > 1:
                paragraph = documento.add_paragraph(header[1])
                paragraph.paragraph_format.space_after = Pt(1)
                paragraph.runs[0].bold = True
                paragraph.runs[0].font.size = Pt(11)
                paragraph.runs[0].font.color.rgb = RGBColor.from_string(self.ACCENT)
                contact_start = 2
            contacts = " • ".join(header[contact_start:])
            if contacts:
                paragraph = documento.add_paragraph(contacts)
                paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
                paragraph.paragraph_format.space_after = Pt(1)
                for run in paragraph.runs:
                    run.font.size = Pt(9.5)
        for section in structure.get("sections", []):
            if not section.get("items"):
                continue
            documento.add_paragraph(section.get("title", "SEÇÃO"), style="Resume Section")
            if section.get("key") == "skills":
                for item in section["items"]:
                    paragraph = documento.add_paragraph()
                    label = paragraph.add_run(f"{item.get('label', 'Competências')}: ")
                    label.bold = True
                    paragraph.add_run(item["text"])
                continue
            if section.get("key") in {"technologies", "languages"}:
                documento.add_paragraph(" | ".join(item["text"] for item in section["items"]))
                continue
            if section.get("key") == "experience":
                for group in self._experience_groups(section):
                    if group["company"]:
                        company = documento.add_paragraph()
                        company.paragraph_format.space_before = Pt(4)
                        company.paragraph_format.space_after = Pt(0)
                        company.paragraph_format.keep_with_next = True
                        company.add_run(group["company"]).bold = True
                    if group["role"] or group["period"]:
                        role = documento.add_paragraph()
                        role.paragraph_format.space_after = Pt(0.5)
                        role.paragraph_format.keep_with_next = True
                        if group["role"]:
                            role.add_run(group["role"]).bold = True
                        if group["role"] and group["period"]:
                            role.add_run(" | ")
                        role.add_run(group["period"])
                    if group["description"]:
                        description = documento.add_paragraph(group["description"])
                        description.paragraph_format.space_after = Pt(1)
                        for run in description.runs:
                            run.font.size = Pt(9.5)
                    for activity in group["activities"]:
                        if ResumeStructureService.normalize(activity) in {
                            "resultados relevantes", "resultados destacados"
                        }:
                            result_label = documento.add_paragraph()
                            result_label.paragraph_format.space_before = Pt(2)
                            result_label.paragraph_format.space_after = Pt(1)
                            result_label.add_run(activity).bold = True
                        else:
                            documento.add_paragraph(
                                re.sub(r"^[•●▪◦\-*–—]\s+", "", activity),
                                style="List Bullet",
                            )
                continue
            for item in section["items"]:
                style = "List Bullet" if item.get("kind") == "bullet" else None
                text = re.sub(r"^[•●▪◦\-*–—]\s+", "", item["text"]) if style else item["text"]
                paragraph = documento.add_paragraph(text, style=style)
                paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
                if item.get("kind") == "position":
                    paragraph.runs[0].bold = True
        destino = Path(destino) if destino else (
            self.output_dir / f"curriculo_direcionado_{datetime.now():%Y%m%d_%H%M%S}.docx"
        )
        destino.parent.mkdir(parents=True, exist_ok=True)
        documento.save(destino)
        return destino

    @staticmethod
    def _resume_structure(dados):
        if dados.get("texto_editado"):
            return ResumeStructureService.from_text(dados["texto_editado"])
        if dados.get("documento"):
            return dados["documento"]
        structure = ResumeStructureService.from_text(dados.get("texto_original", ""))
        structure["sections"].insert(0, {
            "key": "summary", "title": "RESUMO PROFISSIONAL", "source_title": "",
            "items": [{"text": dados.get("resumo_direcionado", ""), "kind": "paragraph"}],
        })
        return structure

    @classmethod
    def _curriculo_blocos(cls, dados):
        """Compatibilidade com integrações antigas sem perder títulos alternativos."""
        structure = cls._resume_structure(dados)
        header = structure.get("header", [])
        name = header[0] if header else "CURRÍCULO"
        blocks: list[tuple[str, Any]] = [
            ("__cabecalho__", (name, " | ".join(header[1:])))
        ]
        blocks.extend(
            (section["title"], [item["text"] for item in section["items"]])
            for section in structure.get("sections", []) if section.get("items")
        )
        return blocks

    def exportar_curriculo_adaptado_pdf(self, dados, destino):
        """Exporta em PDF a mesma estrutura ATS usada pelo DOCX."""
        documento = SimpleDocTemplate(
            str(destino), pagesize=A4,
            leftMargin=1.85 * cm, rightMargin=1.85 * cm,
            topMargin=1.85 * cm, bottomMargin=1.85 * cm,
            title="Currículo direcionado",
        )
        estilos = getSampleStyleSheet()
        regular_font, bold_font = self._register_pdf_fonts()
        accent = HexColor("#" + self.ACCENT)
        nome = ParagraphStyle(
            "NomeCurriculo", parent=estilos["Normal"], fontName=bold_font,
            fontSize=20, leading=22, alignment=TA_LEFT, spaceAfter=2,
        )
        contato = ParagraphStyle(
            "ContatoCurriculo", parent=estilos["Normal"], fontName=regular_font,
            fontSize=9.5, leading=11, alignment=TA_LEFT, spaceAfter=1.5,
        )
        titulo = ParagraphStyle(
            "TituloCurriculo", parent=estilos["Normal"], fontName=bold_font,
            fontSize=13, leading=15, textColor=accent,
            alignment=TA_LEFT, spaceBefore=7, spaceAfter=3,
        )
        corpo = ParagraphStyle(
            "CorpoCurriculo", parent=estilos["Normal"], fontName=regular_font,
            fontSize=10.5, leading=11.6, alignment=TA_LEFT, spaceAfter=1.5,
        )
        bullet_style = ParagraphStyle(
            "BulletCurriculo", parent=corpo, leftIndent=14, bulletIndent=2,
            firstLineIndent=0, spaceAfter=1, leading=11.5,
        )
        historia = []
        structure = self._resume_structure(dados)
        header = structure.get("header", [])
        if header:
            historia.append(Paragraph(self._escapar_pdf(header[0].upper()), nome))
            contact_start = 1
            if dados.get("titulo_direcionado") and len(header) > 1:
                role = ParagraphStyle(
                    "TituloProfissional", parent=contato, fontName=bold_font,
                    fontSize=11, leading=12.5, textColor=accent,
                )
                historia.append(Paragraph(self._escapar_pdf(header[1]), role))
                contact_start = 2
            contacts = " | ".join(header[contact_start:])
            if contacts:
                historia.append(Paragraph(self._escapar_pdf(contacts), contato))
        for section in structure.get("sections", []):
            if not section.get("items"):
                continue
            historia.append(Paragraph(self._escapar_pdf(section["title"]), titulo))
            if section.get("key") == "skills":
                for item in section["items"]:
                    content = (
                        f"<b>{self._escapar_pdf(item.get('label', 'Competências'))}:</b> "
                        f"{self._escapar_pdf(item['text'])}"
                    )
                    historia.append(Paragraph(content, corpo))
                historia.append(Spacer(1, 2))
                continue
            if section.get("key") in {"technologies", "languages"}:
                content = " | ".join(item["text"] for item in section["items"])
                historia.append(Paragraph(self._escapar_pdf(content), corpo))
                historia.append(Spacer(1, 2))
                continue

            if section.get("key") == "experience":
                role_style = ParagraphStyle(
                    "CargoCurriculo", parent=corpo, fontName=bold_font, spaceAfter=0.5,
                )
                company_style = ParagraphStyle(
                    "EmpresaCurriculo", parent=corpo, fontName=bold_font,
                    fontSize=11, leading=12.5, spaceBefore=4, spaceAfter=0,
                )
                description_style = ParagraphStyle(
                    "DescricaoEmpresa", parent=corpo, fontSize=9.5, leading=10.5,
                    textColor=HexColor("#555555"), spaceAfter=1,
                )
                for group in self._experience_groups(section):
                    flowables = []
                    if group["company"]:
                        flowables.append(Paragraph(self._escapar_pdf(group["company"]), company_style))
                    role_line = ""
                    if group["role"]:
                        role_line = self._escapar_pdf(group["role"])
                    if group["period"]:
                        role_line += (" | " if role_line else "") + self._escapar_pdf(group["period"])
                    if role_line:
                        flowables.append(Paragraph(role_line, role_style))
                    if group["description"]:
                        flowables.append(Paragraph(
                            self._escapar_pdf(group["description"]), description_style
                        ))
                    for activity in group["activities"]:
                        normalized = ResumeStructureService.normalize(activity)
                        if normalized in {"resultados relevantes", "resultados destacados"}:
                            flowables.append(Paragraph(
                                f"<b>{self._escapar_pdf(activity)}</b>", corpo
                            ))
                        else:
                            text = re.sub(r"^[•●▪◦\-*–—]\s+", "", activity)
                            flowables.append(Paragraph(
                                self._escapar_pdf(text), bullet_style, bulletText="•"
                            ))
                    historia.append(KeepTogether(flowables))
                historia.append(Spacer(1, 2))
                continue

            def render_item(item):
                text = re.sub(r"^[•●▪◦\-*–—]\s+", "", item["text"])
                if item.get("kind") == "bullet":
                    return Paragraph(self._escapar_pdf(text), bullet_style, bulletText="-")
                style = ParagraphStyle("Position", parent=corpo, fontName=bold_font) if item.get("kind") == "position" else corpo
                return Paragraph(self._escapar_pdf(text), style)

            historia.extend(render_item(item) for item in section["items"])
            historia.append(Spacer(1, 2))
        documento.build(historia)

    @staticmethod
    def _escapar_pdf(texto):
        return (str(texto).replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;").replace("\n", "<br/>"))

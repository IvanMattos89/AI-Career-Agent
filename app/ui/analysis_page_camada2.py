from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QProgressBar,
    QTextEdit
)


class AnalysisPage(QWidget):

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)

        titulo = QLabel("🤖 Análise Inteligente do Currículo")
        titulo.setStyleSheet("""
            font-size:22px;
            font-weight:bold;
            padding:10px;
        """)
        layout.addWidget(titulo)

        self.lbl_cargo = QLabel("Cargo: -")
        self.lbl_area = QLabel("Área: -")
        self.lbl_senioridade = QLabel("Senioridade: -")
        self.lbl_nivel = QLabel("Nível: -")
        self.lbl_experiencia = QLabel("Experiência: -")
        self.lbl_ats = QLabel("ATS Score: -")
        self.lbl_confianca = QLabel("Confiança: 0%")

        for lbl in (
            self.lbl_cargo,
            self.lbl_area,
            self.lbl_senioridade,
            self.lbl_nivel,
            self.lbl_experiencia,
            self.lbl_ats,
            self.lbl_confianca,
        ):
            lbl.setStyleSheet("font-size:15px;padding:4px;")
            layout.addWidget(lbl)

        self.progress = QProgressBar()
        self.progress.setMinimum(0)
        self.progress.setMaximum(100)
        layout.addWidget(self.progress)

        self.editor = QTextEdit()
        self.editor.setReadOnly(True)
        layout.addWidget(self.editor)

    def mostrar_analise(self, analise):

        percentual = int(analise.confianca * 100)

        self.lbl_cargo.setText(f"🎯 Cargo: {analise.cargo}")
        self.lbl_area.setText(f"📂 Área: {analise.area}")
        self.lbl_senioridade.setText(f"⭐ Senioridade: {analise.senioridade}")
        self.lbl_nivel.setText(
            f"🏅 Nível: {getattr(analise, 'nivel_curriculo', '-')}"
        )
        self.lbl_experiencia.setText(
            f"⏳ Experiência: {getattr(analise, 'anos_experiencia', 0)} anos"
        )
        self.lbl_ats.setText(
            f"📈 ATS Score: {getattr(analise, 'ats_score', 0)}"
        )
        self.lbl_confianca.setText(f"Confiança: {percentual}%")

        self.progress.setValue(percentual)

        texto = f"""
══════════════════════════════════════

💪 HARD SKILLS

{chr(10).join('• ' + x for x in analise.hard_skills)}

══════════════════════════════════════

🤝 SOFT SKILLS

{chr(10).join('• ' + x for x in analise.soft_skills)}

══════════════════════════════════════

💻 TECNOLOGIAS

{chr(10).join('• ' + x for x in analise.tecnologias)}

══════════════════════════════════════

🌎 IDIOMAS

{chr(10).join('• ' + x for x in analise.idiomas)}

══════════════════════════════════════

🎓 CERTIFICAÇÕES

{chr(10).join('• ' + x for x in analise.certificacoes)}

══════════════════════════════════════

🔑 PALAVRAS-CHAVE ATS

{chr(10).join('• ' + x for x in getattr(analise, "palavras_chave", []))}

══════════════════════════════════════

⭐ PONTOS FORTES

{chr(10).join('• ' + x for x in getattr(analise, "pontos_fortes", []))}

══════════════════════════════════════

⚠ PONTOS DE MELHORIA

{chr(10).join('• ' + x for x in getattr(analise, "pontos_melhoria", []))}

══════════════════════════════════════

📚 COMPETÊNCIAS FALTANTES

{chr(10).join('• ' + x for x in getattr(analise, "competencias_faltantes", []))}

══════════════════════════════════════

💡 RECOMENDAÇÕES

{chr(10).join('• ' + x for x in getattr(analise, "recomendacoes", []))}

══════════════════════════════════════

📝 RESUMO EXECUTIVO

{analise.resumo}
"""

        self.editor.setPlainText(texto)

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
        self.lbl_confianca = QLabel("Confiança: 0%")

        for lbl in (
            self.lbl_cargo,
            self.lbl_area,
            self.lbl_senioridade,
            self.lbl_confianca
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

        self.lbl_cargo.setText(
            f"Cargo: {analise.cargo}"
        )

        self.lbl_area.setText(
            f"Área: {analise.area}"
        )

        self.lbl_senioridade.setText(
            f"Senioridade: {analise.senioridade}"
        )

        percentual = int(analise.confianca * 100)

        self.lbl_confianca.setText(
            f"Confiança: {percentual}%"
        )

        self.progress.setValue(percentual)

        texto = f"""

Hard Skills

{", ".join(analise.hard_skills)}

Soft Skills

{", ".join(analise.soft_skills)}

Tecnologias

{", ".join(analise.tecnologias)}

Idiomas

{", ".join(analise.idiomas)}

Certificações

{", ".join(analise.certificacoes)}

Resumo

{analise.resumo}

"""

        self.editor.setPlainText(texto)

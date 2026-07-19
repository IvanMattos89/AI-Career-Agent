from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QFileDialog,
    QPlainTextEdit,
    QMessageBox
)

from app.services.resume_service import ResumeService
from app.services.analysis_service import AnalysisService


class ResumePage(QWidget):

    def __init__(self):
        super().__init__()

        self.service = ResumeService()
        self.analysis_service = AnalysisService()

        layout = QVBoxLayout(self)

        self.lbl_titulo = QLabel("Meu Currículo")
        self.lbl_titulo.setStyleSheet("font-size:20px;font-weight:bold;")

        self.lbl_arquivo = QLabel("Nenhum currículo selecionado.")

        self.btn_selecionar = QPushButton("Selecionar Currículo")
        self.btn_selecionar.clicked.connect(self.selecionar_curriculo)

        self.editor = QPlainTextEdit()
        self.editor.setReadOnly(True)

        layout.addWidget(self.lbl_titulo)
        layout.addWidget(self.lbl_arquivo)
        layout.addWidget(self.btn_selecionar)
        layout.addWidget(self.editor)

    def selecionar_curriculo(self):

        arquivo, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar currículo",
            "",
            "Currículos (*.pdf *.docx)"
        )

        if not arquivo:
            return

        try:

            destino, texto = self.service.importar(arquivo)

            self.lbl_arquivo.setText(f"Arquivo: {destino.name}")

            self.editor.setPlainText(texto)

            analise = self.analysis_service.analisar_texto(texto)

            janela = self.window()

            if hasattr(janela, "abrir_analise"):
                janela.abrir_analise(analise)

        except Exception as erro:

            QMessageBox.critical(
                self,
                "Erro",
                str(erro)
            )




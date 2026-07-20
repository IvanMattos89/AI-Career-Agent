from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QTextEdit,
    QPushButton,
    QVBoxLayout,
    QMessageBox
)

from app.ui.widgets.score_card import ScoreCard
from app.ui.widgets.section_card import SectionCard
from app.services.job_match_service import JobMatchService


class JobMatchPage(QWidget):

    def __init__(self):
        super().__init__()

        self.service = JobMatchService()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20,20,20,20)
        layout.setSpacing(15)

        titulo = QLabel("Job Match")
        titulo.setStyleSheet("""
            font-size:28px;
            font-weight:bold;
            color:#1976D2;
        """)

        layout.addWidget(titulo)

        descricao = QLabel("Descrição da vaga")
        descricao.setStyleSheet("""
            font-size:15px;
            font-weight:bold;
        """)

        layout.addWidget(descricao)

        self.txtVaga = QTextEdit()
        self.txtVaga.setPlaceholderText(
            "Cole aqui a descrição completa da vaga..."
        )
        self.txtVaga.setMinimumHeight(180)

        layout.addWidget(self.txtVaga)

        self.btnComparar = QPushButton("Comparar Currículo")
        self.btnComparar.setMinimumHeight(42)
        self.btnComparar.clicked.connect(self.comparar)

        layout.addWidget(self.btnComparar)

        self.score = ScoreCard("Compatibilidade")
        self.score.hide()
        layout.addWidget(self.score)

        self.encontradas = SectionCard("Competências Encontradas")
        self.encontradas.hide()
        layout.addWidget(self.encontradas)

        self.faltantes = SectionCard("Competências Faltantes")
        self.faltantes.hide()
        layout.addWidget(self.faltantes)

        self.recomendacoes = SectionCard("Recomendações")
        self.recomendacoes.hide()
        layout.addWidget(self.recomendacoes)


    def comparar(self):

        vaga = self.txtVaga.toPlainText().strip()

        if not vaga:

            QMessageBox.warning(
                self,
                "Job Match",
                "Cole a descrição da vaga."
            )

            return

        self.btnComparar.setEnabled(False)
        self.btnComparar.setText("Comparando...")

        try:

            resultado = self.service.comparar(vaga)

            self.score.show()
            self.score.setScore(
                int(resultado.get("compatibilidade", 0))
            )

            self.encontradas.show()
            self.encontradas.setItems(
                resultado.get("competencias_encontradas", [])
            )

            self.faltantes.show()
            self.faltantes.setItems(
                resultado.get("competencias_faltantes", [])
            )

            self.recomendacoes.show()
            self.recomendacoes.setItems(
                resultado.get("recomendacoes", [])
            )

        except Exception as erro:

            QMessageBox.critical(
                self,
                "Erro",
                str(erro)
            )

        finally:

            self.btnComparar.setEnabled(True)
            self.btnComparar.setText("Comparar Currículo")

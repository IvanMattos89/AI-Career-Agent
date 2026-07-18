from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PySide6.QtCore import Qt


class DashboardPage(QWidget):

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)

        titulo = QLabel("Dashboard")
        titulo.setAlignment(Qt.AlignCenter)
        titulo.setStyleSheet("font-size:28px;font-weight:bold;")

        texto = QLabel(
            "Bem-vindo ao AI Career Agent.\n\n"
            "Use o menu lateral para acessar as funcionalidades."
        )
        texto.setAlignment(Qt.AlignCenter)

        layout.addStretch()
        layout.addWidget(titulo)
        layout.addWidget(texto)
        layout.addStretch()

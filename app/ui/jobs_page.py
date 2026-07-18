from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PySide6.QtCore import Qt


class JobsPage(QWidget):

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)

        titulo = QLabel("Buscar Vagas")
        titulo.setAlignment(Qt.AlignCenter)
        titulo.setStyleSheet("font-size:26px;font-weight:bold;")

        texto = QLabel("As vagas aparecerão aqui.")
        texto.setAlignment(Qt.AlignCenter)

        layout.addStretch()
        layout.addWidget(titulo)
        layout.addWidget(texto)
        layout.addStretch()

from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PySide6.QtCore import Qt


class SettingsPage(QWidget):

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)

        titulo = QLabel("Configurações")
        titulo.setAlignment(Qt.AlignCenter)
        titulo.setStyleSheet("font-size:26px;font-weight:bold;")

        texto = QLabel("Configurações da aplicação.")
        texto.setAlignment(Qt.AlignCenter)

        layout.addStretch()
        layout.addWidget(titulo)
        layout.addWidget(texto)
        layout.addStretch()

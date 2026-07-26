from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from app.ui.themes.style import *


class InfoCard(QFrame):

    def __init__(self, titulo, valor="", cor=PRIMARY):
        super().__init__()

        self.setMinimumHeight(80)
        self.setStyleSheet(f"""
        QFrame {{
            background:{CARD_BACKGROUND};
            border:1px solid {BORDER};
            border-radius:{CARD_RADIUS}px;
        }}

        QLabel#titulo {{
            border:none;
            color:{TEXT_SECONDARY};
            font-size:11px;
            font-weight:bold;
        }}

        QLabel#valor {{
            border:none;
            color:{cor};
            font-size:24px;
            font-weight:bold;
        }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15,10,15,10)
        layout.setSpacing(4)

        self.lblTitulo = QLabel(titulo)
        self.lblTitulo.setObjectName("titulo")

        self.lblValor = QLabel(valor)
        self.lblValor.setObjectName("valor")
        self.lblValor.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.lblValor.setWordWrap(True)

        layout.addWidget(self.lblTitulo)
        layout.addWidget(self.lblValor)

    def setValue(self, valor):
        self.lblValor.setText(str(valor))

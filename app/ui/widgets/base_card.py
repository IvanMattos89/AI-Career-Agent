from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
from app.ui.themes.style import *


class BaseCard(QFrame):

    def __init__(self, titulo=""):
        super().__init__()

        self.setStyleSheet(f"""
        QFrame {{
            background:{CARD_BACKGROUND};
            border:1px solid {BORDER};
            border-radius:{CARD_RADIUS}px;
        }}

        QLabel {{
            color:{TEXT};
        }}

        QLabel#titulo {{
            font-size:{SUBTITLE_SIZE}px;
            font-weight:bold;
            color:{PRIMARY};
        }}
        """)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(
            CARD_PADDING,
            CARD_PADDING,
            CARD_PADDING,
            CARD_PADDING
        )

        self.lblTitulo = QLabel(titulo)
        self.lblTitulo.setObjectName("titulo")

        self.layout.addWidget(self.lblTitulo)

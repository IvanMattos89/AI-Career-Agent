from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from app.ui.themes.style import *


class SectionCard(QFrame):

    def __init__(self, titulo):
        super().__init__()

        self.setMinimumHeight(130)

        self.setStyleSheet(f"""
        QFrame {{
            background:{CARD_BACKGROUND};
            border:1px solid {BORDER};
            border-radius:{CARD_RADIUS}px;
        }}

        QLabel#titulo {{
            background:{PRIMARY};
            color:white;
            border:none;
            padding:10px;
            font-size:14px;
            font-weight:bold;
        }}

        QLabel#conteudo {{
            border:none;
            padding:12px;
            font-size:12px;
            color:{TEXT};
        }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)

        self.lblTitulo = QLabel(titulo)
        self.lblTitulo.setObjectName("titulo")

        self.lblConteudo = QLabel("-")
        self.lblConteudo.setObjectName("conteudo")
        self.lblConteudo.setWordWrap(True)

        layout.addWidget(self.lblTitulo)
        layout.addWidget(self.lblConteudo)

    def setItems(self, itens):

        if not itens:
            self.hide()
            return

        self.show()

        texto = "\n".join(f"- {item}" for item in itens)

        self.lblConteudo.setText(texto)

    def setText(self, texto):
        self.show()
        self.lblConteudo.setText(texto)

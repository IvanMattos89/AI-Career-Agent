from html import escape

from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from app.ui.themes.style import CARD_BACKGROUND, BORDER, CARD_RADIUS, PRIMARY, TEXT, TEXT_SECONDARY


class SectionCard(QFrame):
    """Card compacto que mantém a grade estável mesmo sem itens."""

    def __init__(self, titulo):
        super().__init__()
        self.setMinimumHeight(142)
        self.setStyleSheet(f"""
            QFrame {{ background:{CARD_BACKGROUND}; border:1px solid {BORDER}; border-radius:{CARD_RADIUS}px; }}
            QLabel#titulo {{ border:none; color:{TEXT}; font-size:14px; font-weight:700; padding:14px 16px 2px; }}
            QLabel#conteudo {{ border:none; color:{TEXT_SECONDARY}; font-size:12px; padding:7px 16px 15px; }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.lblTitulo = QLabel(titulo)
        self.lblTitulo.setObjectName("titulo")
        self.lblConteudo = QLabel("Nenhuma informação identificada")
        self.lblConteudo.setObjectName("conteudo")
        self.lblConteudo.setWordWrap(True)
        layout.addWidget(self.lblTitulo)
        layout.addWidget(self.lblConteudo, 1)

    def setItems(self, itens):
        itens = [str(item).strip() for item in (itens or []) if str(item).strip()]
        if not itens:
            self.lblConteudo.setText("Nenhuma informação identificada")
            return
        chips = " ".join(
            f'<span style="background:#EAF3FF; color:{PRIMARY}; padding:5px 8px; border-radius:8px;">{escape(item)}</span>'
            for item in itens
        )
        self.lblConteudo.setText(chips)

    def setText(self, texto):
        self.lblConteudo.setText(escape(str(texto or "Nenhuma informação identificada")))

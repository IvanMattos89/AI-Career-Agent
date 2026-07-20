from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QVBoxLayout,
    QProgressBar
)

from app.ui.themes.style import *


class ScoreCard(QFrame):

    def __init__(self, titulo="ATS SCORE"):
        super().__init__()

        self.setMinimumHeight(145)

        self.setStyleSheet(f"""
        QFrame {{
            background:{CARD_BACKGROUND};
            border:1px solid {BORDER};
            border-radius:{CARD_RADIUS}px;
        }}

        QLabel#titulo {{
            border:none;
            font-size:13px;
            font-weight:bold;
            color:{TEXT_SECONDARY};
        }}

        QLabel#score {{
            border:none;
            font-size:46px;
            font-weight:bold;
            color:{PRIMARY};
        }}

        QLabel#status {{
            border:none;
            font-size:14px;
            font-weight:bold;
            color:{TEXT_SECONDARY};
        }}

        QProgressBar {{
            border:1px solid #CCCCCC;
            border-radius:8px;
            height:24px;
            text-align:center;
        }}

        QProgressBar::chunk {{
            border-radius:7px;
            background:{PRIMARY};
        }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18,18,18,18)
        layout.setSpacing(8)

        self.lblTitulo = QLabel(titulo)
        self.lblTitulo.setObjectName("titulo")

        self.lblScore = QLabel("0")
        self.lblScore.setObjectName("score")

        self.progress = QProgressBar()
        self.progress.setMaximum(100)

        self.lblStatus = QLabel("-")
        self.lblStatus.setObjectName("status")

        layout.addWidget(self.lblTitulo)
        layout.addWidget(self.lblScore)
        layout.addWidget(self.progress)
        layout.addWidget(self.lblStatus)

    def setScore(self, valor):

        valor = max(0, min(100, int(valor)))

        self.lblScore.setText(str(valor))
        self.progress.setValue(valor)

        if valor >= 80:
            texto = "Excelente"
            cor = SUCCESS

        elif valor >= 60:
            texto = "Bom"
            cor = WARNING

        elif valor >= 40:
            texto = "Regular"
            cor = "#EF6C00"

        else:
            texto = "Precisa Melhorar"
            cor = DANGER

        self.lblStatus.setText(texto)

        self.lblScore.setStyleSheet(f"""
            border:none;
            font-size:46px;
            font-weight:bold;
            color:{cor};
        """)

        self.progress.setStyleSheet(f"""
        QProgressBar {{
            border:1px solid #CCCCCC;
            border-radius:8px;
            height:24px;
            text-align:center;
        }}

        QProgressBar::chunk {{
            border-radius:7px;
            background:{cor};
        }}
        """)

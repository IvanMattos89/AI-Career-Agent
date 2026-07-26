from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from app.ui.themes.style import *


class RecentAnalysisCard(QFrame):

    def __init__(self, cargo="-", ats="-", data="-"):
        super().__init__()

        self.setMinimumHeight(90)

        self.setStyleSheet(f"""
        QFrame {{
            background:{CARD_BACKGROUND};
            border:1px solid {BORDER};
            border-radius:{CARD_RADIUS}px;
        }}

        QLabel {{
            border:none;
        }}

        QLabel#cargo {{
            font-size:15px;
            font-weight:bold;
            color:{PRIMARY};
        }}

        QLabel#info {{
            font-size:12px;
            color:{TEXT_SECONDARY};
        }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12,10,12,10)
        layout.setSpacing(4)

        self.lblCargo = QLabel(cargo)
        self.lblCargo.setObjectName("cargo")

        self.lblInfo = QLabel(f"ATS: {ats}    |    {data}")
        self.lblInfo.setObjectName("info")

        layout.addWidget(self.lblCargo)
        layout.addWidget(self.lblInfo)

    def atualizar(self, cargo, ats, data):
        self.lblCargo.setText(cargo)
        self.lblInfo.setText(f"ATS: {ats}    |    {data}")

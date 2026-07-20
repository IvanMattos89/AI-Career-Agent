from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QGridLayout
)

from app.ui.widgets.info_card import InfoCard
from app.ui.widgets.recent_analysis_card import RecentAnalysisCard
from app.services.dashboard_service import DashboardService


class DashboardPage(QWidget):

    def __init__(self):
        super().__init__()

        self.service = DashboardService()

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20,20,20,20)
        self.layout.setSpacing(20)

        titulo = QLabel("Dashboard")
        titulo.setStyleSheet("""
            font-size:28px;
            font-weight:bold;
            color:#1976D2;
            padding:5px;
        """)

        self.layout.addWidget(titulo)

        grid = QGridLayout()

        self.cardATS = InfoCard("ATS Médio", "0")
        self.cardCurriculos = InfoCard("Currículos", "0")
        self.cardVagas = InfoCard("Vagas", "-")
        self.cardUltima = InfoCard("Último Cargo", "-")

        grid.addWidget(self.cardATS,0,0)
        grid.addWidget(self.cardCurriculos,0,1)
        grid.addWidget(self.cardVagas,0,2)
        grid.addWidget(self.cardUltima,0,3)

        for i in range(4):
            grid.setColumnStretch(i,1)

        self.layout.addLayout(grid)

        tituloHistorico = QLabel("Últimas análises")
        tituloHistorico.setStyleSheet("""
            font-size:18px;
            font-weight:bold;
            color:#1976D2;
            margin-top:15px;
        """)

        self.layout.addWidget(tituloHistorico)

        self.listaHistorico = QVBoxLayout()
        self.listaHistorico.setSpacing(10)

        self.layout.addLayout(self.listaHistorico)

        self.carregar_dados()


    def carregar_dados(self):

        dados = self.service.indicadores()

        self.cardATS.setValue(str(dados["ats"]))
        self.cardCurriculos.setValue(str(dados["curriculos"]))
        self.cardVagas.setValue("-")
        self.cardUltima.setValue(dados["cargo"])

        self.carregar_historico()


    def carregar_historico(self):

        while self.listaHistorico.count():

            item = self.listaHistorico.takeAt(0)

            if item.widget():
                item.widget().deleteLater()

        historico = self.service.ultimas_analises()

        if not historico:

            self.listaHistorico.addWidget(
                RecentAnalysisCard(
                    "Nenhuma análise encontrada",
                    "-",
                    "-"
                )
            )

            return

        for item in historico:

            self.listaHistorico.addWidget(

                RecentAnalysisCard(

                    cargo=item["cargo"] or "-",

                    ats=item["ats_score"] or "-",

                    data=item["created_at"][:10]
                )
            )

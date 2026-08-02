from PySide6.QtWidgets import QGridLayout, QLabel, QVBoxLayout, QWidget

from app.services.dashboard_service import DashboardService
from app.ui.widgets.info_card import InfoCard
from app.ui.widgets.recent_analysis_card import RecentAnalysisCard


class DashboardPage(QWidget):

    def __init__(self):
        super().__init__()

        self.service = DashboardService()

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(28,24,28,24)
        self.layout.setSpacing(18)

        titulo = QLabel("Dashboard")
        titulo.setObjectName("pageTitle")

        self.layout.addWidget(titulo)

        grid = QGridLayout()

        self.cardATS = InfoCard("Qualidade ATS média", "0")
        self.cardCurriculos = InfoCard("Currículos", "0")
        self.cardVagas = InfoCard("Job Matches", "0")
        self.cardUltima = InfoCard("Último Cargo", "-")
        self.cardCandidaturas = InfoCard("Candidaturas", "0")
        self.cardEntrevistas = InfoCard("Taxa de entrevistas", "0%")
        self.cardAcompanhamentos = InfoCard("Ações pendentes", "0")
        self.cardFonte = InfoCard("Fonte eficiente", "-")

        grid.addWidget(self.cardATS,0,0)
        grid.addWidget(self.cardCurriculos,0,1)
        grid.addWidget(self.cardVagas,0,2)
        grid.addWidget(self.cardUltima,0,3)
        grid.addWidget(self.cardCandidaturas,1,0)
        grid.addWidget(self.cardEntrevistas,1,1)
        grid.addWidget(self.cardAcompanhamentos,1,2)
        grid.addWidget(self.cardFonte,1,3)

        for i in range(4):
            grid.setColumnStretch(i,1)

        self.layout.addLayout(grid)

        tituloHistorico = QLabel("Últimas análises")
        tituloHistorico.setObjectName("sectionTitle")

        self.layout.addWidget(tituloHistorico)

        self.listaHistorico = QVBoxLayout()
        self.listaHistorico.setSpacing(10)

        self.layout.addLayout(self.listaHistorico)

        self.carregar_dados()


    def carregar_dados(self):

        dados = self.service.indicadores()

        self.cardATS.setValue(str(dados["ats"]))
        self.cardCurriculos.setValue(str(dados["curriculos"]))
        self.cardVagas.setValue(f'{dados["job_matches"]} ({dados["match_medio"]}%)')
        self.cardUltima.setValue(dados["cargo"])
        self.cardCandidaturas.setValue(str(dados["candidaturas"]))
        self.cardEntrevistas.setValue(f'{dados["taxa_entrevistas"]}%')
        self.cardAcompanhamentos.setValue(str(dados["acompanhamentos"]))
        self.cardFonte.setValue(dados["melhor_fonte"])

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

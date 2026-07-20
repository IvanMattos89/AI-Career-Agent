from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QGridLayout,
    QLabel,
    QScrollArea,
    QFrame,
)

from app.ui.widgets.score_card import ScoreCard
from app.ui.widgets.info_card import InfoCard
from app.ui.widgets.section_card import SectionCard


class AnalysisPage(QWidget):

    def __init__(self):
        super().__init__()
        self._criar_interface()

    # =====================================================
    # INTERFACE
    # =====================================================

    def _criar_interface(self):

        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(20,20,20,20)

        titulo = QLabel("Analise Inteligente do Curriculo")
        titulo.setStyleSheet("""
            QLabel{
                font-size:28px;
                font-weight:bold;
                color:#1976D2;
                padding:8px;
            }
        """)

        layout_principal.addWidget(titulo)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        layout_principal.addWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)

        self.layout = QVBoxLayout(container)
        self.layout.setContentsMargins(25,25,25,25)
        self.layout.setSpacing(20)

        self._criar_score()
        self._criar_metricas()
        self._criar_cards()

    # =====================================================
    # SCORE
    # =====================================================

    def _criar_score(self):

        self.score = ScoreCard()

        self.layout.addWidget(self.score)

    # =====================================================
    # MÉTRICAS
    # =====================================================

    def _criar_metricas(self):

        grid = QGridLayout()

        grid.setHorizontalSpacing(15)
        grid.setVerticalSpacing(20)

        self.cardCargo = InfoCard("Cargo")
        self.cardArea = InfoCard("Área")
        self.cardSenioridade = InfoCard("Senioridade")
        self.cardExperiencia = InfoCard("Experiência")
        self.cardConfianca = InfoCard("Confiança")

        grid.addWidget(self.cardCargo, 0, 0)
        grid.addWidget(self.cardArea, 0, 1)
        grid.addWidget(self.cardSenioridade, 0, 2)
        grid.addWidget(self.cardExperiencia, 0, 3)
        grid.addWidget(self.cardConfianca, 0, 4)

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)
        grid.setColumnStretch(3, 1)
        grid.setColumnStretch(4, 1)

        self.layout.addLayout(grid)
    # =====================================================
    # CARDS DE ANÁLISE
    # =====================================================

    def _criar_cards(self):

        grid = QGridLayout()

        grid.setHorizontalSpacing(15)
        grid.setVerticalSpacing(20)

        # ---------- Linha 1 ----------

        self.cardHardSkills = SectionCard("Hard Skills")
        self.cardSoftSkills = SectionCard("Soft Skills")

        grid.addWidget(self.cardHardSkills, 0, 0)
        grid.addWidget(self.cardSoftSkills, 0, 1)

        # ---------- Linha 2 ----------

        self.cardTecnologias = SectionCard("Tecnologias")
        self.cardIdiomas = SectionCard("Idiomas")

        grid.addWidget(self.cardTecnologias, 1, 0)
        grid.addWidget(self.cardIdiomas, 1, 1)

        # ---------- Linha 3 ----------

        self.cardCertificacoes = SectionCard("Certificações")
        self.cardPalavras = SectionCard("Palavras-chave ATS")

        grid.addWidget(self.cardCertificacoes, 2, 0)
        grid.addWidget(self.cardPalavras, 2, 1)

        # ---------- Linha 4 ----------

        self.cardFortes = SectionCard("Pontos Fortes")
        self.cardMelhorias = SectionCard("Pontos de Melhoria")

        grid.addWidget(self.cardFortes, 3, 0)
        grid.addWidget(self.cardMelhorias, 3, 1)

        # ---------- Linha 5 ----------

        self.cardCompetencias = SectionCard("Competências Faltantes")
        self.cardRecomendacoes = SectionCard("Recomendações")

        grid.addWidget(self.cardCompetencias, 4, 0)
        grid.addWidget(self.cardRecomendacoes, 4, 1)

        # ---------- Responsividade ----------

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        self.layout.addLayout(grid)

        # ---------- Resumo ----------

        self.cardResumo = SectionCard("Resumo Executivo")

        self.layout.addWidget(self.cardResumo)
    # =====================================================
    # ATUALIZA A ANÁLISE
    # =====================================================

    def mostrar_analise(self, analise):

        # ---------- Score ----------

        ats = getattr(analise, "ats_score", 0)
        self.score.setScore(ats)

        # ---------- Cards superiores ----------

        self.cardCargo.setValue(
            getattr(analise, "cargo", "-")
        )

        self.cardArea.setValue(
            getattr(analise, "area", "-")
        )

        self.cardSenioridade.setValue(
            getattr(analise, "senioridade", "-")
        )

        anos = getattr(
            analise,
            "anos_experiencia",
            0
        )

        self.cardExperiencia.setValue(
            f"{anos} anos"
        )

        confianca = int(
            getattr(
                analise,
                "confianca",
                0
            ) * 100
        )

        self.cardConfianca.setValue(
            f"{confianca}%"
        )

        # ---------- Cards laterais ----------

        self.cardHardSkills.setItems(
            getattr(
                analise,
                "hard_skills",
                []
            )
        )

        self.cardSoftSkills.setItems(
            getattr(
                analise,
                "soft_skills",
                []
            )
        )

        self.cardTecnologias.setItems(
            getattr(
                analise,
                "tecnologias",
                []
            )
        )

        self.cardIdiomas.setItems(
            getattr(
                analise,
                "idiomas",
                []
            )
        )

        self.cardCertificacoes.setItems(
            getattr(
                analise,
                "certificacoes",
                []
            )
        )

        self.cardPalavras.setItems(
            getattr(
                analise,
                "palavras_chave",
                []
            )
        )

        self.cardFortes.setItems(
            getattr(
                analise,
                "pontos_fortes",
                []
            )
        )

        self.cardMelhorias.setItems(
            getattr(
                analise,
                "pontos_melhoria",
                []
            )
        )

        self.cardCompetencias.setItems(
            getattr(
                analise,
                "competencias_faltantes",
                []
            )
        )

        self.cardRecomendacoes.setItems(
            getattr(
                analise,
                "recomendacoes",
                []
            )
        )

        resumo = getattr(
            analise,
            "resumo",
            "-"
        )

        self.cardResumo.lblConteudo.setText(resumo)


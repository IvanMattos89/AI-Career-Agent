from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QGridLayout,
    QLabel,
    QScrollArea,
    QFrame,
)

from types import SimpleNamespace

from app.database.sqlite_db import Database
from app.ui.widgets.score_card import ScoreCard
from app.ui.widgets.info_card import InfoCard
from app.ui.widgets.section_card import SectionCard


class AnalysisPage(QWidget):

    def __init__(self):
        super().__init__()
        self.db = Database()
        self._criar_interface()
        self.carregar_ultima_analise()

    # =====================================================
    # INTERFACE
    # =====================================================

    def _criar_interface(self):

        layout_principal = QVBoxLayout(self)
        layout_principal.setContentsMargins(20,20,20,20)

        titulo = QLabel("Análise inteligente do currículo")
        titulo.setStyleSheet("""
            QLabel{
                font-size:28px;
                font-weight:bold;
                color:#1976D2;
                padding:8px;
            }
        """)

        layout_principal.addWidget(titulo)

        subtitulo = QLabel("Veja os pontos fortes do perfil e os próximos ajustes recomendados para aumentar a aderência às vagas.")
        subtitulo.setStyleSheet("color:#667085;font-size:13px;padding:0 8px 8px;")
        layout_principal.addWidget(subtitulo)

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

    @staticmethod
    def _lista(valor):
        return [item.strip() for item in (valor or "").split(";") if item.strip()]

    def carregar_ultima_analise(self):
        """Reabre a última análise persistida ao entrar nesta tela."""
        registro = self.db.obter_ultima_analise()
        if not registro:
            return False
        habilidades = self._lista(registro["hard_skills"])
        analise = SimpleNamespace(
            ats_score=registro["ats_score"] or 0,
            cargo=registro["cargo"] or "Não identificado",
            area=registro["area"] or "Não identificada",
            senioridade=registro["senioridade"] or "Em análise",
            anos_experiencia=registro["anos_experiencia"] or 0,
            confianca=None,
            hard_skills=habilidades,
            soft_skills=self._lista(registro["soft_skills"]),
            tecnologias=self._lista(registro["tecnologias"]),
            idiomas=self._lista(registro["idiomas"]),
            certificacoes=self._lista(registro["certificacoes"]),
            palavras_chave=self._lista(registro["palavras_chave"]) or habilidades,
            pontos_fortes=self._lista(registro["pontos_fortes"]) or habilidades[:5],
            pontos_melhoria=self._lista(registro["pontos_melhoria"]),
            competencias_faltantes=self._lista(registro["competencias_faltantes"]),
            recomendacoes=self._lista(registro["recomendacoes"]) or [
                "Inclua resultados mensuráveis nas experiências mais relevantes.",
                "Adapte o resumo profissional às palavras-chave da vaga antes de candidatar.",
            ],
            resumo=registro["resumo"] or "Resumo não disponível.",
        )
        self.mostrar_analise(analise)
        return True

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

        confianca = getattr(analise, "confianca", None)
        self.cardConfianca.setValue(
            f"{int(confianca * 100)}%" if isinstance(confianca, (int, float)) else "Não registrada"
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

        self.cardResumo.setText(resumo)


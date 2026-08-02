from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent, QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.config import APP_NAME, APP_VERSION
from app.ui.history_page import HistoryPage
from app.ui.pages.analysis_page import AnalysisPage
from app.ui.pages.career_hub_page import CareerHubPage
from app.ui.pages.dashboard_page import DashboardPage
from app.ui.pages.job_match_page import JobMatchPage
from app.ui.resume_page import ResumePage
from app.ui.settings_page import SettingsPage


class MainWindow(QMainWindow):
    """Janela principal com navegação persistente e estado visual ativo."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.resize(1480, 900)
        self.setMinimumSize(1080, 700)

        central = QWidget()
        central.setObjectName("appRoot")
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(252)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(18, 22, 18, 18)
        sidebar_layout.setSpacing(7)

        marca = QHBoxLayout()
        marca.setSpacing(10)
        badge = QLabel("AI")
        badge.setObjectName("brandBadge")
        badge.setAlignment(Qt.AlignCenter)
        badge.setFixedSize(42, 42)
        textos = QVBoxLayout()
        textos.setSpacing(0)
        titulo = QLabel("AI Career Agent")
        titulo.setObjectName("brandTitle")
        versao = QLabel(f"Career workspace • v{APP_VERSION}")
        versao.setObjectName("brandVersion")
        textos.addWidget(titulo)
        textos.addWidget(versao)
        marca.addWidget(badge)
        marca.addLayout(textos, 1)
        sidebar_layout.addLayout(marca)
        sidebar_layout.addSpacing(24)

        self.btn_dashboard = self._nav_button("◈  Dashboard")
        self.btn_jobs = self._nav_button("⌕  Buscar vagas")
        self.btn_resume = self._nav_button("▤  Meu currículo")
        self.btn_history = self._nav_button("◷  Histórico")
        self.btn_analysis = self._nav_button("✦  Análise IA")
        self.btn_hub = self._nav_button("↗  Central de Carreira")
        self.btn_settings = self._nav_button("⚙  Configurações")
        self.nav_buttons = [
            self.btn_dashboard,
            self.btn_jobs,
            self.btn_resume,
            self.btn_history,
            self.btn_analysis,
            self.btn_hub,
            self.btn_settings,
        ]
        for botao in self.nav_buttons:
            sidebar_layout.addWidget(botao)
        sidebar_layout.addStretch()
        rodape = QLabel("Dados locais protegidos\nIA externa somente com consentimento")
        rodape.setObjectName("sidebarFooter")
        rodape.setWordWrap(True)
        sidebar_layout.addWidget(rodape)

        self.stack = QStackedWidget()
        self.dashboard_page = DashboardPage()
        self.job_match_page = JobMatchPage()
        self.resume_page = ResumePage()
        self.history_page = HistoryPage()
        self.analysis_page = AnalysisPage()
        self.career_hub_page = CareerHubPage()
        self.settings_page = SettingsPage()
        for pagina in (
            self.dashboard_page,
            self.job_match_page,
            self.resume_page,
            self.history_page,
            self.analysis_page,
            self.career_hub_page,
            self.settings_page,
        ):
            self.stack.addWidget(pagina)

        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.stack, 1)

        self.btn_dashboard.clicked.connect(self.abrir_dashboard)
        self.btn_jobs.clicked.connect(self.abrir_job_match)
        self.btn_resume.clicked.connect(lambda: self._abrir_pagina(2))
        self.btn_history.clicked.connect(self._abrir_historico)
        self.btn_analysis.clicked.connect(self.abrir_analise_salva)
        self.btn_hub.clicked.connect(self.abrir_central_carreira)
        self.btn_settings.clicked.connect(self._abrir_configuracoes)
        self.career_hub_page.busca_integrada_solicitada.connect(
            self.abrir_busca_integrada_da_central
        )

        self._abrir_pagina(0)
        self._shutting_down = False

    def shutdown_background_tasks(self):
        """Finaliza todos os workers antes que o Qt destrua suas páginas."""
        if self._shutting_down:
            return
        self._shutting_down = True
        pages = (
            self.dashboard_page,
            self.resume_page,
            self.job_match_page,
            self.history_page,
            self.analysis_page,
            self.career_hub_page,
            self.settings_page,
        )
        for page in pages:
            shutdown = getattr(page, "shutdown", None)
            if callable(shutdown):
                shutdown()
        for page in pages:
            for owner in (page, getattr(page, "service", None)):
                database = getattr(owner, "db", None)
                if database is not None:
                    database.close()

    def closeEvent(self, event: QCloseEvent):
        self.shutdown_background_tasks()
        super().closeEvent(event)

    @staticmethod
    def _nav_button(texto):
        botao = QPushButton(texto)
        botao.setProperty("nav", True)
        botao.setCheckable(True)
        botao.setCursor(Qt.PointingHandCursor)
        botao.setFont(QFont("Segoe UI", 10))
        return botao

    def _abrir_pagina(self, indice):
        self.stack.setCurrentIndex(indice)
        for posicao, botao in enumerate(self.nav_buttons):
            botao.setChecked(posicao == indice)

    def _abrir_historico(self):
        self.history_page.carregar_curriculos()
        self._abrir_pagina(3)

    def _abrir_configuracoes(self):
        self.settings_page.atualizar_resumo()
        self._abrir_pagina(6)

    def abrir_analise(self, analise):
        self.analysis_page.mostrar_analise(analise)
        self._abrir_pagina(4)

    def abrir_analise_salva(self):
        self.analysis_page.carregar_ultima_analise()
        self._abrir_pagina(4)

    def abrir_dashboard(self):
        self.dashboard_page.carregar_dados()
        self._abrir_pagina(0)

    def preparar_vagas_para_curriculo(self):
        self.job_match_page.carregar_curriculo_ativo()
        self.job_match_page.buscar_para_curriculo(silencioso=True)

    def abrir_job_match(self):
        self.job_match_page.carregar_curriculo_ativo()
        self._abrir_pagina(1)

    def abrir_central_carreira(self):
        self.career_hub_page.atualizar_perfil()
        self.career_hub_page.carregar_oportunidades()
        self._abrir_pagina(5)

    def abrir_busca_integrada_da_central(self):
        self.abrir_job_match()
        self.job_match_page.buscar_para_curriculo()

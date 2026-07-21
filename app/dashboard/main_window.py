from PySide6.QtCore import Qt


from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QMainWindow,
    QStackedWidget
)

from app.ui.pages.job_match_page import JobMatchPage
from app.ui.resume_page import ResumePage
from app.ui.history_page import HistoryPage
from app.ui.settings_page import SettingsPage
from app.ui.pages.analysis_page import AnalysisPage
from app.ui.pages.dashboard_page import DashboardPage
from app.ui.pages.career_hub_page import CareerHubPage
from app.config import APP_NAME, APP_VERSION


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.resize(1400, 800)

        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0,0,0,0)
        main_layout.setSpacing(0)

        sidebar = QWidget()
        sidebar.setFixedWidth(260)
        sidebar.setStyleSheet("""
            background:#2f3542;
            color:white;
        """)

        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(20,20,20,20)

        titulo = QLabel("AI Career Agent")
        titulo.setAlignment(Qt.AlignCenter)
        titulo.setStyleSheet("""
            font-size:18px;
            font-weight:bold;
            padding:20px;
        """)

        sidebar_layout.addWidget(titulo)

        self.btn_dashboard = QPushButton("🏠 Dashboard")
        self.btn_jobs = QPushButton("🔍 Buscar vagas")
        self.btn_resume = QPushButton("📄 Meu currículo")
        self.btn_history = QPushButton("📜 Histórico")
        self.btn_analysis = QPushButton("🤖 Análise IA")
        self.btn_hub = QPushButton("🚀 Central de Carreira")
        self.btn_settings = QPushButton("⚙ Configurações")

        botoes = [
            self.btn_dashboard,
            self.btn_jobs,
            self.btn_resume,
            self.btn_history,
            self.btn_analysis,
            self.btn_hub,
            self.btn_settings
        ]

        for botao in botoes:
            botao.setCursor(Qt.PointingHandCursor)
            botao.setMinimumHeight(45)
            botao.setStyleSheet("""
                QPushButton{
                    color:white;
                    background:transparent;
                    border:none;
                    text-align:left;
                    padding-left:10px;
                    font-size:15px;
                }

                QPushButton:hover{
                    background:#57606f;
                }
            """)
            sidebar_layout.addWidget(botao)

        sidebar_layout.addStretch()

        self.stack = QStackedWidget()

        self.dashboard_page = DashboardPage()
        self.job_match_page = JobMatchPage()
        self.resume_page = ResumePage()
        self.history_page = HistoryPage()
        self.analysis_page = AnalysisPage()
        self.career_hub_page = CareerHubPage()
        self.settings_page = SettingsPage()

        self.stack.addWidget(self.dashboard_page)
        self.stack.addWidget(self.job_match_page)
        self.stack.addWidget(self.resume_page)
        self.stack.addWidget(self.history_page)
        self.stack.addWidget(self.analysis_page)
        self.stack.addWidget(self.career_hub_page)
        self.stack.addWidget(self.settings_page)

        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.stack)

        self.btn_dashboard.clicked.connect(self.abrir_dashboard)

        self.btn_jobs.clicked.connect(self.abrir_job_match)

        self.btn_resume.clicked.connect(
            lambda: self.stack.setCurrentIndex(2)
        )

        self.btn_history.clicked.connect(
            lambda: self.stack.setCurrentIndex(3)
        )

        self.btn_analysis.clicked.connect(self.abrir_analise_salva)

        self.btn_hub.clicked.connect(self.abrir_central_carreira)
        self.career_hub_page.busca_integrada_solicitada.connect(self.abrir_busca_integrada_da_central)

        self.btn_settings.clicked.connect(
            lambda: self.stack.setCurrentIndex(6)
        )

        self.stack.setCurrentIndex(0)
        # A busca automática ocorre após uma nova análise; não iniciamos
        # chamadas de rede silenciosas a cada abertura do aplicativo.

    def abrir_analise(self, analise):

        self.analysis_page.mostrar_analise(analise)
        self.stack.setCurrentIndex(4)

        self.setStyleSheet("""

            QMainWindow{
                background:white;
            }

            QLabel{
                color:#222;
            }

            QStackedWidget{
                background:white;
            }

        """)

    def abrir_analise_salva(self):
        self.analysis_page.carregar_ultima_analise()
        self.stack.setCurrentIndex(4)

    def abrir_dashboard(self):
        self.dashboard_page.carregar_dados()
        self.stack.setCurrentIndex(0)

    def preparar_vagas_para_curriculo(self):
        """Chamado após uma nova análise; não executa automaticamente na abertura."""
        self.job_match_page.carregar_curriculo_ativo()
        self.job_match_page.buscar_para_curriculo(silencioso=True)

    def abrir_job_match(self):
        self.job_match_page.carregar_curriculo_ativo()
        self.stack.setCurrentIndex(1)

    def abrir_central_carreira(self):
        self.career_hub_page.atualizar_perfil()
        self.career_hub_page.carregar_oportunidades()
        self.stack.setCurrentIndex(5)

    def abrir_busca_integrada_da_central(self):
        self.abrir_job_match()
        self.job_match_page.buscar_para_curriculo()




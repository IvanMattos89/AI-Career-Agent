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

from app.ui.dashboard_page import DashboardPage
from app.ui.jobs_page import JobsPage
from app.ui.resume_page import ResumePage
from app.ui.history_page import HistoryPage
from app.ui.settings_page import SettingsPage
from app.ui.analysis_page import AnalysisPage


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("AI Career Agent")
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
        self.btn_settings = QPushButton("⚙ Configurações")

        botoes = [
            self.btn_dashboard,
            self.btn_jobs,
            self.btn_resume,
            self.btn_history,
            self.btn_analysis,
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
        self.jobs_page = JobsPage()
        self.resume_page = ResumePage()
        self.history_page = HistoryPage()
        self.analysis_page = AnalysisPage()
        self.settings_page = SettingsPage()

        self.stack.addWidget(self.dashboard_page)
        self.stack.addWidget(self.jobs_page)
        self.stack.addWidget(self.resume_page)
        self.stack.addWidget(self.history_page)
        self.stack.addWidget(self.analysis_page)
        self.stack.addWidget(self.settings_page)

        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.stack)

        self.btn_dashboard.clicked.connect(
            lambda: self.stack.setCurrentIndex(0)
        )

        self.btn_jobs.clicked.connect(
            lambda: self.stack.setCurrentIndex(1)
        )

        self.btn_resume.clicked.connect(
            lambda: self.stack.setCurrentIndex(2)
        )

        self.btn_history.clicked.connect(
            lambda: self.stack.setCurrentIndex(3)
        )

        self.btn_analysis.clicked.connect(
            lambda: self.stack.setCurrentIndex(4)
        )

        self.btn_settings.clicked.connect(
            lambda: self.stack.setCurrentIndex(5)
        )

        self.stack.setCurrentIndex(0)

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



import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from app.ai.logging_config import logger
from app.dashboard.main_window import MainWindow
from app.ui.themes.style import application_stylesheet


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("AI Career Agent")
    app.setStyle("Fusion")
    app.setStyleSheet(application_stylesheet())

    def report_unhandled(exception_type, exception, traceback):
        logger.critical(
            "Erro não tratado na interface",
            exc_info=(exception_type, exception, traceback),
        )
        QMessageBox.critical(
            None, "AI Career Agent",
            "Ocorreu um erro inesperado. Nenhum dado foi enviado. Consulte o log em Configurações.",
        )

    sys.excepthook = report_unhandled
    window = MainWindow()
    app.aboutToQuit.connect(window.shutdown_background_tasks)
    window.show()
    sys.exit(app.exec())

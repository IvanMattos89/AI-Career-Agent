import sys

from PySide6.QtWidgets import QApplication

from app.dashboard.main_window import MainWindow
from app.ui.themes.style import application_stylesheet


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("AI Career Agent")
    app.setStyle("Fusion")
    app.setStyleSheet(application_stylesheet())
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

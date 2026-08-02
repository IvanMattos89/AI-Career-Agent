import unittest

from PySide6.QtWidgets import QApplication

from app.config import APP_VERSION
from app.dashboard.main_window import MainWindow


class MainWindowSmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_builds_all_pages_and_navigates_without_network_calls(self):
        window = MainWindow()
        self.addCleanup(window.close)

        self.assertEqual(window.stack.count(), 7)
        self.assertIn(APP_VERSION, window.windowTitle())
        window.abrir_dashboard()
        self.assertEqual(window.stack.currentIndex(), 0)
        window.abrir_job_match()
        self.assertEqual(window.stack.currentIndex(), 1)
        window.abrir_analise_salva()
        self.assertEqual(window.stack.currentIndex(), 4)
        window.abrir_central_carreira()
        self.assertEqual(window.stack.currentIndex(), 5)
        window._abrir_configuracoes()
        self.assertEqual(window.stack.currentIndex(), 6)
        window.shutdown_background_tasks()

from pathlib import Path

from PySide6.QtCore import QThread
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog, QPlainTextEdit, QMessageBox

from app.services.resume_service import ResumeService
from app.ui.workers import ResumeAnalysisWorker, ResumeImportWorker


class ResumePage(QWidget):
    def __init__(self):
        super().__init__()
        self.service = ResumeService()
        self.thread = None
        self.worker = None
        self.import_thread = None
        self.import_worker = None
        layout = QVBoxLayout(self)
        self.lbl_titulo = QLabel("Meu Currículo")
        self.lbl_titulo.setStyleSheet("font-size:20px;font-weight:bold;")
        self.lbl_arquivo = QLabel("Nenhum currículo selecionado.")
        self.btn_selecionar = QPushButton("Selecionar Currículo")
        self.btn_selecionar.clicked.connect(self.selecionar_curriculo)
        self.editor = QPlainTextEdit()
        self.editor.setReadOnly(True)
        for widget in (self.lbl_titulo, self.lbl_arquivo, self.btn_selecionar, self.editor):
            layout.addWidget(widget)

    def selecionar_curriculo(self):
        arquivo, _ = QFileDialog.getOpenFileName(self, "Selecionar currículo", "", "Currículos (*.pdf *.docx)")
        if not arquivo:
            return
        if self.import_thread or self.thread:
            return
        self.btn_selecionar.setEnabled(False)
        self.btn_selecionar.setText("Importando currículo...")
        self.import_thread = QThread(self)
        self.import_worker = ResumeImportWorker(arquivo)
        self.import_worker.moveToThread(self.import_thread)
        self.import_thread.started.connect(self.import_worker.run)
        self.import_worker.finished.connect(self.importacao_concluida)
        self.import_worker.failed.connect(self.importacao_falhou)
        self.import_worker.finished.connect(self.import_thread.quit)
        self.import_worker.failed.connect(self.import_thread.quit)
        self.import_thread.finished.connect(self.finalizar_importacao)
        self.import_thread.finished.connect(self.import_worker.deleteLater)
        self.import_thread.finished.connect(self.import_thread.deleteLater)
        self.import_thread.start()

    def importacao_concluida(self, resume_id, destino, texto):
        self.lbl_arquivo.setText(f"Arquivo: {Path(destino).name}")
        self.editor.setPlainText(texto)
        self.iniciar_analise(resume_id, texto)

    def importacao_falhou(self, mensagem):
        QMessageBox.warning(self, "Importação do currículo", mensagem)

    def finalizar_importacao(self):
        self.import_thread = None
        self.import_worker = None
        if not self.thread:
            self.btn_selecionar.setEnabled(True)
            self.btn_selecionar.setText("Selecionar Currículo")

    def iniciar_analise(self, resume_id, texto):
        self.btn_selecionar.setText("Analisando currículo...")
        self.thread = QThread(self)
        self.worker = ResumeAnalysisWorker(resume_id, texto)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.analise_concluida)
        self.worker.failed.connect(self.analise_falhou)
        self.worker.finished.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.thread.finished.connect(self.finalizar_analise)
        self.thread.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def analise_concluida(self, analise):
        janela = self.window()
        if hasattr(janela, "abrir_analise"):
            janela.abrir_analise(analise)
        if hasattr(janela, "preparar_vagas_para_curriculo"):
            janela.preparar_vagas_para_curriculo()

    def analise_falhou(self, mensagem):
        QMessageBox.critical(self, "Erro", mensagem)

    def finalizar_analise(self):
        self.btn_selecionar.setEnabled(True)
        self.btn_selecionar.setText("Selecionar Currículo")
        self.thread = None
        self.worker = None

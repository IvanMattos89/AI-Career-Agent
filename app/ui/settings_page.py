from pathlib import Path

from dotenv import set_key
from PySide6.QtCore import Qt, QThread
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit,
    QPushButton, QComboBox, QGroupBox, QMessageBox, QCheckBox,
)

from app.ai.config import AIConfig, ENV_FILE
from app.config import DATABASE, REPORTS_DIR
from app.database.sqlite_db import Database
from app.ui.workers import OllamaStatusWorker


class SettingsPage(QWidget):
    """Configurações persistentes e diagnóstico das dependências locais."""

    def __init__(self):
        super().__init__()
        self.db = Database()
        self.ollama_thread = None
        self.ollama_worker = None
        self._criar_interface()
        self.atualizar_resumo()

    def _criar_interface(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        titulo = QLabel("Configurações")
        titulo.setStyleSheet("font-size:28px;font-weight:bold;color:#1976D2;")
        layout.addWidget(titulo)
        descricao = QLabel("Ajuste a integração de IA e consulte o estado dos dados locais. Alterações de IA são aplicadas no próximo reinício.")
        descricao.setWordWrap(True)
        layout.addWidget(descricao)

        grupo_ia = QGroupBox("Inteligência artificial")
        form_ia = QFormLayout(grupo_ia)
        self.provider = QComboBox()
        self.provider.addItem("Automático (Ollama, depois OpenAI)", "auto")
        self.provider.addItem("Somente Ollama local", "ollama")
        self.provider.addItem("Somente OpenAI", "openai")
        indice = self.provider.findData(AIConfig.PROVIDER)
        self.provider.setCurrentIndex(max(0, indice))
        self.ollama_url = QLineEdit(AIConfig.OLLAMA_URL)
        self.ollama_model = QLineEdit(AIConfig.OLLAMA_MODEL)
        self.ollama_timeout = QLineEdit(str(AIConfig.OLLAMA_TIMEOUT))
        self.openai_model = QLineEdit(AIConfig.OPENAI_MODEL)
        self.openai_model.setToolTip("A chave da OpenAI permanece somente no arquivo .env e não é exibida aqui.")
        self.openai_consent = QCheckBox("Autorizo o envio do currículo para a OpenAI quando este provedor for utilizado.")
        self.openai_consent.setChecked(AIConfig.OPENAI_DATA_CONSENT)
        self.openai_consent.setToolTip("O currículo pode conter dados pessoais. Sem esta autorização, a aplicação usa Ollama local ou a análise local.")
        form_ia.addRow("Provedor", self.provider)
        form_ia.addRow("URL do Ollama", self.ollama_url)
        form_ia.addRow("Modelo do Ollama", self.ollama_model)
        form_ia.addRow("Timeout do Ollama (segundos)", self.ollama_timeout)
        form_ia.addRow("Modelo OpenAI", self.openai_model)
        form_ia.addRow("Privacidade OpenAI", self.openai_consent)
        layout.addWidget(grupo_ia)

        acoes_ia = QHBoxLayout()
        self.btn_salvar = QPushButton("Salvar configurações")
        self.btn_salvar.clicked.connect(self.salvar)
        self.btn_testar = QPushButton("Testar conexão Ollama")
        self.btn_testar.clicked.connect(self.testar_ollama)
        self.lbl_ollama = QLabel("Status: ainda não testado")
        acoes_ia.addWidget(self.btn_salvar)
        acoes_ia.addWidget(self.btn_testar)
        acoes_ia.addWidget(self.lbl_ollama)
        acoes_ia.addStretch()
        layout.addLayout(acoes_ia)

        grupo_dados = QGroupBox("Dados e recursos locais")
        form_dados = QFormLayout(grupo_dados)
        self.lbl_curriculos = QLabel()
        self.lbl_matches = QLabel()
        self.lbl_oportunidades = QLabel()
        self.lbl_banco = QLabel(str(DATABASE.resolve()))
        self.lbl_relatorios = QLabel(str(REPORTS_DIR.resolve()))
        self.lbl_fontes = QLabel("Remotive e Arbeitnow (fontes públicas); vagas manuais também são suportadas.")
        self.lbl_fontes.setWordWrap(True)
        form_dados.addRow("Currículos importados", self.lbl_curriculos)
        form_dados.addRow("Job Matches salvos", self.lbl_matches)
        form_dados.addRow("Oportunidades salvas", self.lbl_oportunidades)
        form_dados.addRow("Banco SQLite", self.lbl_banco)
        form_dados.addRow("Diretório de relatórios", self.lbl_relatorios)
        form_dados.addRow("Fontes de vagas", self.lbl_fontes)
        layout.addWidget(grupo_dados)

        acoes_dados = QHBoxLayout()
        btn_atualizar = QPushButton("Atualizar informações")
        btn_atualizar.clicked.connect(self.atualizar_resumo)
        btn_relatorios = QPushButton("Abrir relatórios")
        btn_relatorios.clicked.connect(lambda: self.abrir_pasta(REPORTS_DIR))
        acoes_dados.addWidget(btn_atualizar)
        acoes_dados.addWidget(btn_relatorios)
        acoes_dados.addStretch()
        layout.addLayout(acoes_dados)
        layout.addStretch()

    def atualizar_resumo(self):
        self.lbl_curriculos.setText(str(self.db.dashboard_total_curriculos()))
        self.lbl_matches.setText(str(self.db.dashboard_job_match_metricas()["total"]))
        self.lbl_oportunidades.setText(str(len(self.db.listar_oportunidades())))

    def salvar(self):
        Path(ENV_FILE).touch(exist_ok=True)
        valores = {
            "AI_PROVIDER": self.provider.currentData(),
            "OLLAMA_URL": self.ollama_url.text().strip(),
            "OLLAMA_MODEL": self.ollama_model.text().strip(),
            "OLLAMA_TIMEOUT": self.ollama_timeout.text().strip(),
            "OPENAI_MODEL": self.openai_model.text().strip(),
            "OPENAI_DATA_CONSENT": "true" if self.openai_consent.isChecked() else "false",
        }
        if not all(valores.values()) or not valores["OLLAMA_TIMEOUT"].isdigit() or int(valores["OLLAMA_TIMEOUT"]) < 5:
            QMessageBox.warning(self, "Configurações", "Preencha todos os campos de IA antes de salvar.")
            return
        for chave, valor in valores.items():
            set_key(ENV_FILE, chave, valor)
        QMessageBox.information(self, "Configurações salvas", "Configurações salvas no .env. Reinicie o aplicativo para aplicar o novo provedor ou modelo.")

    def testar_ollama(self):
        if self.ollama_thread:
            return
        self.btn_testar.setEnabled(False)
        self.lbl_ollama.setText("Status: testando conexão...")
        self.ollama_thread = QThread(self)
        self.ollama_worker = OllamaStatusWorker(self.ollama_url.text().strip())
        self.ollama_worker.moveToThread(self.ollama_thread)
        self.ollama_thread.started.connect(self.ollama_worker.run)
        self.ollama_worker.finished.connect(self.receber_status_ollama)
        self.ollama_worker.finished.connect(self.ollama_thread.quit)
        self.ollama_thread.finished.connect(self.finalizar_teste_ollama)
        self.ollama_thread.finished.connect(self.ollama_worker.deleteLater)
        self.ollama_thread.finished.connect(self.ollama_thread.deleteLater)
        self.ollama_thread.start()

    def receber_status_ollama(self, disponivel, mensagem):
        self.lbl_ollama.setText(f"Status: {mensagem}")

    def finalizar_teste_ollama(self):
        self.btn_testar.setEnabled(True)
        self.ollama_thread = None
        self.ollama_worker = None

    @staticmethod
    def abrir_pasta(pasta):
        pasta.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(pasta.resolve())))

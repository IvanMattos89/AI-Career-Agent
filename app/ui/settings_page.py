"""Configurações organizadas, diagnóstico e privacidade do aplicativo."""

import os
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from dotenv import set_key
from PySide6.QtCore import QThread, QUrl
from PySide6.QtGui import QDesktopServices, QIntValidator
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.ai.config import ENV_FILE, AIConfig
from app.ai.logging_config import LOG_DIR
from app.config import DATABASE, REPORTS_DIR
from app.database.sqlite_db import Database
from app.ui.workers import OllamaStatusWorker, shutdown_threads


class SettingsPage(QWidget):
    """Central clara para IA, fontes de vagas e dados pessoais locais."""

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
        layout.setSpacing(14)

        title = QLabel("Configurações")
        title.setObjectName("pageTitle")
        subtitle = QLabel(
            "Gerencie serviços de IA, fontes de vagas e dados locais com privacidade e diagnóstico."
        )
        subtitle.setObjectName("pageSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        self.feedback = QLabel("Configurações carregadas. Nenhuma alteração pendente.")
        self.feedback.setObjectName("settingsFeedback")
        self.feedback.setProperty("state", "neutral")
        self.feedback.setWordWrap(True)
        layout.addWidget(self.feedback)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._aba_ia(), "Inteligência artificial")
        self.tabs.addTab(self._aba_fontes(), "Busca de vagas")
        self.tabs.addTab(self._aba_dados(), "Dados e privacidade")
        layout.addWidget(self.tabs, 1)

        footer = QHBoxLayout()
        self.btn_salvar = QPushButton("Salvar alterações")
        self.btn_salvar.clicked.connect(self.salvar)
        footer.addStretch()
        footer.addWidget(self.btn_salvar)
        layout.addLayout(footer)

    @staticmethod
    def _scroll_tab():
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        container = QWidget()
        content = QVBoxLayout(container)
        content.setContentsMargins(18, 18, 18, 18)
        content.setSpacing(14)
        scroll.setWidget(container)
        return scroll, content

    @staticmethod
    def _helper(text):
        label = QLabel(text)
        label.setObjectName("mutedText")
        label.setWordWrap(True)
        return label

    def _aba_ia(self):
        tab, layout = self._scroll_tab()
        layout.addWidget(self._helper(
            "Ollama mantém os dados no computador quando usa uma URL local. OpenAI e Ollama remoto "
            "só recebem dados após autorização explícita."
        ))

        provider_group = QGroupBox("Provedor e modelos")
        form = QFormLayout(provider_group)
        self.provider = QComboBox()
        self.provider.addItem("Automático — prioriza Ollama local", "auto")
        self.provider.addItem("Somente Ollama", "ollama")
        self.provider.addItem("Somente OpenAI", "openai")
        self.provider.setCurrentIndex(max(0, self.provider.findData(AIConfig.PROVIDER)))
        self.ollama_url = QLineEdit(AIConfig.OLLAMA_URL)
        self.ollama_url.setPlaceholderText("http://localhost:11434")
        self.ollama_model = QLineEdit(AIConfig.OLLAMA_MODEL)
        self.ollama_timeout = QLineEdit(str(AIConfig.OLLAMA_TIMEOUT))
        self.ollama_timeout.setValidator(QIntValidator(5, 600, self))
        self.ollama_timeout.setMaximumWidth(160)
        self.openai_model = QLineEdit(AIConfig.OPENAI_MODEL)
        self.openai_key = self._secret_field(AIConfig.OPENAI_API_KEY, "Chave da API OpenAI")
        form.addRow("Estratégia", self.provider)
        form.addRow("URL do Ollama", self.ollama_url)
        form.addRow("Modelo Ollama", self.ollama_model)
        form.addRow("Timeout (segundos)", self.ollama_timeout)
        form.addRow("Modelo OpenAI", self.openai_model)
        form.addRow("Chave OpenAI", self.openai_key)
        layout.addWidget(provider_group)

        privacy_group = QGroupBox("Consentimento e privacidade")
        privacy_layout = QVBoxLayout(privacy_group)
        self.openai_consent = QCheckBox(
            "Autorizo o envio do currículo para a OpenAI quando esse provedor for utilizado."
        )
        self.openai_consent.setChecked(AIConfig.OPENAI_DATA_CONSENT)
        self.ollama_external_consent = QCheckBox(
            "Autorizo o envio ao Ollama quando a URL não for local."
        )
        self.ollama_external_consent.setChecked(AIConfig.OLLAMA_EXTERNAL_CONSENT)
        privacy_layout.addWidget(self.openai_consent)
        privacy_layout.addWidget(self.ollama_external_consent)
        privacy_layout.addWidget(self._helper(
            "Sem consentimento ou provedor disponível, o aplicativo utiliza a análise local."
        ))
        layout.addWidget(privacy_group)

        actions = QHBoxLayout()
        self.btn_testar = QPushButton("Testar Ollama")
        self.btn_testar.setProperty("secondary", True)
        self.btn_testar.clicked.connect(self.testar_ollama)
        self.lbl_ollama = QLabel("Não testado")
        self.lbl_ollama.setObjectName("serviceStatus")
        self.lbl_ollama.setProperty("state", "neutral")
        actions.addWidget(self.btn_testar)
        actions.addWidget(self.lbl_ollama)
        actions.addStretch()
        layout.addLayout(actions)
        layout.addStretch()
        return tab

    def _aba_fontes(self):
        tab, layout = self._scroll_tab()
        self.provider_summary = QLabel()
        self.provider_summary.setObjectName("settingsSummary")
        self.provider_summary.setWordWrap(True)
        layout.addWidget(self.provider_summary)

        profile_group = QGroupBox("Preferências da busca")
        profile_form = QFormLayout(profile_group)
        self.target_titles = QLineEdit(os.getenv("JOB_TARGET_TITLES", ""))
        self.target_titles.setPlaceholderText("Analista Fiscal Sênior, Especialista Fiscal")
        profile_form.addRow("Cargos-alvo", self.target_titles)
        profile_form.addRow("", self._helper(
            "Separe os títulos por vírgula. Eles complementam os cargos identificados no currículo."
        ))
        layout.addWidget(profile_group)

        company_group = QGroupBox("Plataformas por empresa")
        company_form = QFormLayout(company_group)
        self.greenhouse_boards = QLineEdit(os.getenv("JOB_GREENHOUSE_BOARDS", ""))
        self.greenhouse_boards.setPlaceholderText("tokens de boards separados por vírgula")
        self.lever_sites = QLineEdit(os.getenv("JOB_LEVER_SITES", ""))
        self.lever_sites.setPlaceholderText("sites Lever separados por vírgula")
        self.gupy_token = self._secret_field(os.getenv("GUPY_API_TOKEN", ""), "Token oficial Gupy")
        company_form.addRow("Greenhouse", self.greenhouse_boards)
        company_form.addRow("Lever", self.lever_sites)
        company_form.addRow("Gupy", self.gupy_token)
        company_form.addRow("", self._helper(
            "Essas APIs consultam somente as empresas ou a organização configurada; não são catálogos globais."
        ))
        layout.addWidget(company_group)

        aggregator_group = QGroupBox("Agregadores e fontes complementares")
        aggregator_form = QFormLayout(aggregator_group)
        self.adzuna_id = QLineEdit(os.getenv("ADZUNA_APP_ID", ""))
        self.adzuna_id.setPlaceholderText("App ID")
        self.adzuna_key = self._secret_field(os.getenv("ADZUNA_APP_KEY", ""), "App key")
        self.jooble_key = self._secret_field(os.getenv("JOOBLE_API_KEY", ""), "Chave da API")
        self.enable_arbeitnow = QCheckBox("Ativar Arbeitnow")
        self.enable_arbeitnow.setChecked(self._env_bool("JOB_ENABLE_ARBEITNOW"))
        aggregator_form.addRow("Adzuna App ID", self.adzuna_id)
        aggregator_form.addRow("Adzuna App Key", self.adzuna_key)
        aggregator_form.addRow("Jooble", self.jooble_key)
        aggregator_form.addRow("Arbeitnow", self.enable_arbeitnow)
        layout.addWidget(aggregator_group)

        self.show_secrets = QCheckBox("Mostrar credenciais nesta tela")
        self.show_secrets.toggled.connect(self._alternar_segredos)
        layout.addWidget(self.show_secrets)

        metrics_group = QGroupBox("Desempenho das fontes")
        metrics_layout = QVBoxLayout(metrics_group)
        self.lbl_metricas_fontes = QLabel("Nenhuma busca registrada.")
        self.lbl_metricas_fontes.setWordWrap(True)
        metrics_layout.addWidget(self.lbl_metricas_fontes)
        layout.addWidget(metrics_group)

        for field in (
            self.greenhouse_boards, self.lever_sites, self.gupy_token, self.adzuna_id,
            self.adzuna_key, self.jooble_key,
        ):
            field.textChanged.connect(self._atualizar_status_provedores)
        self.enable_arbeitnow.toggled.connect(self._atualizar_status_provedores)
        layout.addStretch()
        return tab

    def _aba_dados(self):
        tab, layout = self._scroll_tab()
        cards = QGridLayout()
        self.lbl_curriculos = self._metric_card("Currículos")
        self.lbl_matches = self._metric_card("Job Matches")
        self.lbl_oportunidades = self._metric_card("Candidaturas")
        self.lbl_integridade = self._metric_card("Banco de dados")
        for index, card in enumerate((
            self.lbl_curriculos, self.lbl_matches, self.lbl_oportunidades, self.lbl_integridade,
        )):
            cards.addWidget(card[0], 0, index)
        layout.addLayout(cards)

        paths_group = QGroupBox("Armazenamento local")
        paths_form = QFormLayout(paths_group)
        self.lbl_banco = QLabel(str(DATABASE.resolve()))
        self.lbl_banco.setTextInteractionFlags(self.lbl_banco.textInteractionFlags())
        self.lbl_relatorios = QLabel(str(REPORTS_DIR.resolve()))
        paths_form.addRow("Banco SQLite", self.lbl_banco)
        paths_form.addRow("Relatórios", self.lbl_relatorios)
        paths_form.addRow("Logs", QLabel(str(LOG_DIR.resolve())))
        layout.addWidget(paths_group)

        privacy = QLabel(
            "Os dados ficam neste computador, mas não são criptografados em repouso. O backup pode "
            "conter currículo, histórico e dados pessoais; armazene-o em local protegido."
        )
        privacy.setObjectName("privacyNotice")
        privacy.setWordWrap(True)
        layout.addWidget(privacy)

        actions = QHBoxLayout()
        refresh = QPushButton("Atualizar diagnóstico")
        refresh.setProperty("secondary", True)
        refresh.clicked.connect(self.atualizar_resumo)
        backup = QPushButton("Criar backup do banco")
        backup.clicked.connect(self.criar_backup)
        reports = QPushButton("Abrir relatórios")
        reports.setProperty("secondary", True)
        reports.clicked.connect(lambda: self.abrir_pasta(REPORTS_DIR))
        logs = QPushButton("Abrir logs")
        logs.setProperty("secondary", True)
        logs.clicked.connect(lambda: self.abrir_pasta(LOG_DIR))
        for button in (refresh, backup, reports, logs):
            actions.addWidget(button)
        actions.addStretch()
        layout.addLayout(actions)
        layout.addStretch()
        return tab

    @staticmethod
    def _metric_card(title):
        frame = QFrame()
        frame.setObjectName("settingsMetric")
        box = QVBoxLayout(frame)
        label = QLabel(title)
        label.setObjectName("metricLabel")
        value = QLabel("—")
        value.setObjectName("metricValue")
        box.addWidget(label)
        box.addWidget(value)
        return frame, value

    @staticmethod
    def _secret_field(value, placeholder):
        field = QLineEdit(value)
        field.setEchoMode(QLineEdit.Password)
        field.setPlaceholderText(placeholder)
        return field

    @staticmethod
    def _env_bool(key):
        return os.getenv(key, "false").strip().casefold() in {"1", "true", "yes", "sim"}

    def _alternar_segredos(self, visible):
        mode = QLineEdit.Normal if visible else QLineEdit.Password
        for field in (self.openai_key, self.gupy_token, self.adzuna_key, self.jooble_key):
            field.setEchoMode(mode)

    def _atualizar_status_provedores(self):
        active = ["Vagas.com", "Remotive"]
        pending = []
        if self.greenhouse_boards.text().strip():
            active.append("Greenhouse")
        else:
            pending.append("Greenhouse")
        if self.lever_sites.text().strip():
            active.append("Lever")
        else:
            pending.append("Lever")
        if self.gupy_token.text().strip():
            active.append("Gupy")
        else:
            pending.append("Gupy")
        adzuna_complete = bool(self.adzuna_id.text().strip() and self.adzuna_key.text().strip())
        if adzuna_complete:
            active.append("Adzuna")
        else:
            pending.append("Adzuna")
        if self.jooble_key.text().strip():
            active.append("Jooble")
        else:
            pending.append("Jooble")
        if self.enable_arbeitnow.isChecked():
            active.append("Arbeitnow")
        self.provider_summary.setText(
            f"<b>{len(active)} fontes ativas:</b> {', '.join(active)}<br>"
            f"<span style='color:#64748B'>Opcionais não configuradas: {', '.join(pending) or 'nenhuma'}.</span>"
        )

    def atualizar_resumo(self):
        self.lbl_curriculos[1].setText(str(self.db.dashboard_total_curriculos()))
        self.lbl_matches[1].setText(str(self.db.dashboard_job_match_metricas()["total"]))
        self.lbl_oportunidades[1].setText(str(len(self.db.listar_oportunidades())))
        diagnostic = self.db.diagnostico()
        size_mb = diagnostic["tamanho_bytes"] / (1024 * 1024)
        status = (
            "Íntegro"
            if diagnostic["integridade"] == "ok" and diagnostic.get("violacoes_fk", 0) == 0
            else "Verificar"
        )
        self.lbl_integridade[1].setText(f"{status} · v{diagnostic['migracao']} · {size_mb:.1f} MB")
        metrics = self.db.metricas_provedores()
        if metrics:
            self.lbl_metricas_fontes.setText("<br>".join(
                f"<b>{item['provider']}</b> — {item['brasil'] or 0} Brasil de "
                f"{item['recebidas'] or 0} recebidas · {item['falhas']} falhas · "
                f"{int(item['tempo_medio_ms'] or 0)} ms em média"
                for item in metrics
            ))
        else:
            self.lbl_metricas_fontes.setText("Nenhuma busca registrada.")
        self._atualizar_status_provedores()

    def _valores(self):
        return {
            "AI_PROVIDER": self.provider.currentData(),
            "OLLAMA_URL": self.ollama_url.text().strip(),
            "OLLAMA_MODEL": self.ollama_model.text().strip(),
            "OLLAMA_TIMEOUT": self.ollama_timeout.text().strip(),
            "OPENAI_MODEL": self.openai_model.text().strip(),
            "OPENAI_API_KEY": self.openai_key.text().strip(),
            "OPENAI_DATA_CONSENT": "true" if self.openai_consent.isChecked() else "false",
            "OLLAMA_EXTERNAL_CONSENT": "true" if self.ollama_external_consent.isChecked() else "false",
            "JOB_GREENHOUSE_BOARDS": self.greenhouse_boards.text().strip(),
            "JOB_LEVER_SITES": self.lever_sites.text().strip(),
            "JOB_ENABLE_ARBEITNOW": "true" if self.enable_arbeitnow.isChecked() else "false",
            "JOB_TARGET_TITLES": self.target_titles.text().strip(),
            "GUPY_API_TOKEN": self.gupy_token.text().strip(),
            "ADZUNA_APP_ID": self.adzuna_id.text().strip(),
            "ADZUNA_APP_KEY": self.adzuna_key.text().strip(),
            "JOOBLE_API_KEY": self.jooble_key.text().strip(),
        }

    @staticmethod
    def _validar(valores):
        if not valores["OLLAMA_MODEL"] or not valores["OPENAI_MODEL"]:
            return "Informe os modelos de IA."
        if not valores["OLLAMA_TIMEOUT"].isdigit() or not 5 <= int(valores["OLLAMA_TIMEOUT"]) <= 600:
            return "O timeout do Ollama deve estar entre 5 e 600 segundos."
        url = urlparse(valores["OLLAMA_URL"])
        if url.scheme not in {"http", "https"} or not url.hostname:
            return "Informe uma URL HTTP ou HTTPS válida para o Ollama."
        if bool(valores["ADZUNA_APP_ID"]) != bool(valores["ADZUNA_APP_KEY"]):
            return "Adzuna exige App ID e App Key preenchidos em conjunto."
        return ""

    def salvar(self):
        values = self._valores()
        error = self._validar(values)
        if error:
            self._feedback(error, "error")
            self.tabs.setCurrentIndex(1 if "Adzuna" in error else 0)
            return
        Path(ENV_FILE).touch(exist_ok=True)
        for key, value in values.items():
            set_key(ENV_FILE, key, value)
            os.environ[key] = value
        self._feedback(
            "Alterações salvas. Fontes de vagas já usam os novos dados; reinicie apenas para "
            "trocar o provedor ou modelo de IA.",
            "success",
        )
        self.atualizar_resumo()

    def _feedback(self, message, state):
        self.feedback.setText(message)
        self.feedback.setProperty("state", state)
        self.feedback.style().unpolish(self.feedback)
        self.feedback.style().polish(self.feedback)

    def testar_ollama(self):
        values = self._valores()
        error = self._validar(values)
        if error and "Adzuna" not in error:
            self._feedback(error, "error")
            return
        if self.ollama_thread:
            return
        self.btn_testar.setEnabled(False)
        self.lbl_ollama.setText("Testando…")
        self.lbl_ollama.setProperty("state", "warning")
        self.ollama_thread = QThread(self)
        self.ollama_worker = OllamaStatusWorker(
            self.ollama_url.text().strip(), self.ollama_model.text().strip()
        )
        self.ollama_worker.moveToThread(self.ollama_thread)
        self.ollama_thread.started.connect(self.ollama_worker.run)
        self.ollama_worker.finished.connect(self.receber_status_ollama)
        self.ollama_worker.finished.connect(self.ollama_thread.quit)
        self.ollama_thread.finished.connect(self.finalizar_teste_ollama)
        self.ollama_thread.finished.connect(self.ollama_worker.deleteLater)
        self.ollama_thread.finished.connect(self.ollama_thread.deleteLater)
        self.ollama_thread.start()

    def receber_status_ollama(self, available, message):
        self.lbl_ollama.setText(message)
        self.lbl_ollama.setProperty("state", "success" if available else "error")
        self.lbl_ollama.style().unpolish(self.lbl_ollama)
        self.lbl_ollama.style().polish(self.lbl_ollama)

    def finalizar_teste_ollama(self):
        self.btn_testar.setEnabled(True)
        self.ollama_thread = None
        self.ollama_worker = None

    def shutdown(self):
        """Interrompe o diagnóstico do Ollama durante a saída."""
        shutdown_threads((self.ollama_thread,))

    def criar_backup(self):
        default = f"ai_career_agent_backup_{datetime.now():%Y%m%d_%H%M%S}.db"
        path, _ = QFileDialog.getSaveFileName(self, "Salvar backup", default, "Banco SQLite (*.db)")
        if not path:
            return
        try:
            destination = self.db.criar_backup(path)
            self._feedback(f"Backup criado em {destination}", "success")
        except (OSError, ValueError) as error:
            self._feedback(f"Não foi possível criar o backup: {error}", "error")

    @staticmethod
    def abrir_pasta(folder):
        folder.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder.resolve())))

import json
from html import escape
from urllib.parse import quote_plus

from PySide6.QtCore import QThread, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.database.sqlite_db import Database
from app.services.job_search_service import JobSearchService
from app.services.report_service import ReportService
from app.services.resume_adaptation_service import ResumeAdaptationService
from app.ui.resume_preview_dialog import ResumePreviewDialog
from app.ui.widgets.score_card import ScoreCard
from app.ui.widgets.section_card import SectionCard
from app.ui.workers import (
    JobBatchMatchWorker,
    JobMatchWorker,
    JobSearchWorker,
    shutdown_threads,
)


class JobMatchPage(QWidget):
    def __init__(self):
        super().__init__()
        self.resultado_atual = None
        self.thread = None
        self.worker = None
        self.search_thread = None
        self.search_worker = None
        self.batch_thread = None
        self.batch_worker = None
        self.vagas_encontradas = []
        self.titulo_vaga_atual = None
        self.busca_silenciosa = False
        self.curriculo_adaptado = None
        self.db = Database()
        self.relatorios = ReportService()

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        container = QWidget()
        scroll.setWidget(container)
        outer_layout.addWidget(scroll)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(12)
        titulo = QLabel("Job Match")
        titulo.setObjectName("pageTitle")
        layout.addWidget(titulo)
        self.perfil_ativo = QLabel()
        self.perfil_ativo.setWordWrap(True)
        self.perfil_ativo.setObjectName("profileBanner")
        layout.addWidget(self.perfil_ativo)
        layout.addWidget(QLabel("Buscar vagas no Brasil automaticamente"))
        busca = QHBoxLayout()
        self.txtBusca = QLineEdit()
        self.txtBusca.setPlaceholderText("Ex.: analista fiscal, Python, data analyst")
        self.txtBusca.returnPressed.connect(self.buscar_vagas)
        self.cmbEstado = QComboBox()
        self.cmbEstado.addItem("Todo o Brasil", "")
        for sigla, nome in JobSearchService.ESTADOS_BRASIL.items():
            self.cmbEstado.addItem(f"{sigla} — {nome}", sigla)
        self.txtCidade = QLineEdit()
        self.txtCidade.setPlaceholderText("Cidade (opcional)")
        self.txtCidade.setMaximumWidth(190)
        self.cmbModalidade = QComboBox()
        self.cmbModalidade.addItem("Qualquer modalidade", "")
        self.cmbModalidade.addItem("Remoto", "Remoto")
        self.cmbModalidade.addItem("Híbrido", "Híbrido")
        self.cmbModalidade.addItem("Presencial", "Presencial")
        self.cmbSenioridade = QComboBox()
        self.cmbSenioridade.addItem("Qualquer senioridade", "")
        for nivel in ("Júnior", "Pleno", "Sênior", "Especialista", "Coordenação", "Gerência"):
            self.cmbSenioridade.addItem(nivel, nivel)
        self.btnBuscar = QPushButton("Buscar vagas")
        self.btnBuscar.clicked.connect(self.buscar_vagas)
        self.btnBuscarPerfil = QPushButton("Buscar para meu currículo")
        self.btnBuscarPerfil.clicked.connect(self.buscar_para_curriculo)
        self.btnGoogle = QPushButton("Pesquisar no Google")
        self.btnGoogle.clicked.connect(lambda: self.abrir_pesquisa_externa("Google"))
        self.btnLinkedIn = QPushButton("LinkedIn")
        self.btnLinkedIn.clicked.connect(lambda: self.abrir_pesquisa_externa("LinkedIn"))
        self.btnIndeed = QPushButton("Indeed")
        self.btnIndeed.clicked.connect(lambda: self.abrir_pesquisa_externa("Indeed"))
        self.btnGupy = QPushButton("Gupy")
        self.btnGupy.clicked.connect(lambda: self.abrir_pesquisa_externa("Gupy"))
        self.btnAbrirVaga = QPushButton("Abrir vaga selecionada")
        self.btnAbrirVaga.clicked.connect(self.abrir_vaga_selecionada)
        for botao in (
            self.btnBuscarPerfil, self.btnGoogle, self.btnLinkedIn, self.btnIndeed,
            self.btnGupy, self.btnAbrirVaga,
        ):
            botao.setProperty("secondary", True)
        busca.addWidget(self.txtBusca)
        busca.addWidget(self.cmbEstado)
        busca.addWidget(self.txtCidade)
        busca.addWidget(self.cmbModalidade)
        busca.addWidget(self.cmbSenioridade)
        layout.addLayout(busca)
        acoes_busca = QHBoxLayout()
        for botao in (self.btnBuscar, self.btnBuscarPerfil):
            acoes_busca.addWidget(botao)
        acoes_busca.addStretch()
        layout.addLayout(acoes_busca)
        fontes_externas = QHBoxLayout()
        for botao in (
            self.btnGoogle, self.btnLinkedIn, self.btnIndeed, self.btnGupy, self.btnAbrirVaga,
        ):
            fontes_externas.addWidget(botao)
        fontes_externas.addStretch()
        layout.addLayout(fontes_externas)
        self.resultados_busca = QTableWidget(0, 7)
        self.resultados_busca.setHorizontalHeaderLabels(
            ["Vaga", "Empresa", "Localização", "Fonte", "Ranking", "Decisão", "Match"]
        )
        self.resultados_busca.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.resultados_busca.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.resultados_busca.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.resultados_busca.setMaximumHeight(190)
        self.resultados_busca.cellDoubleClicked.connect(self.usar_vaga_selecionada)
        layout.addWidget(self.resultados_busca)
        decisoes = QHBoxLayout()
        self.btnFavoritar = QPushButton("Favoritar")
        self.btnDescartar = QPushButton("Descartar")
        self.btnCandidatura = QPushButton("Criar candidatura")
        self.btnFavoritar.setProperty("secondary", True)
        self.btnDescartar.setProperty("danger", True)
        self.btnFavoritar.clicked.connect(self.favoritar_vaga)
        self.btnDescartar.clicked.connect(self.descartar_vaga)
        self.btnCandidatura.clicked.connect(self.converter_em_candidatura)
        decisoes.addWidget(self.btnFavoritar)
        decisoes.addWidget(self.btnDescartar)
        decisoes.addWidget(self.btnCandidatura)
        decisoes.addStretch()
        layout.addLayout(decisoes)
        self.resumo_fontes = QLabel("As métricas de cada fonte aparecerão após a busca.")
        self.resumo_fontes.setObjectName("mutedText")
        self.resumo_fontes.setWordWrap(True)
        layout.addWidget(self.resumo_fontes)
        self.btnCompararTodas = QPushButton("Comparar todas as vagas encontradas")
        self.btnCompararTodas.setEnabled(False)
        self.btnCompararTodas.clicked.connect(self.comparar_todas)
        layout.addWidget(self.btnCompararTodas)
        self.btnCancelarLote = QPushButton("Cancelar comparação em lote")
        self.btnCancelarLote.setProperty("secondary", True)
        self.btnCancelarLote.setEnabled(False)
        self.btnCancelarLote.clicked.connect(self.cancelar_lote)
        layout.addWidget(self.btnCancelarLote)
        layout.addWidget(QLabel("Descrição da vaga"))

        self.txtVaga = QTextEdit()
        self.txtVaga.setPlaceholderText("Cole aqui a descrição completa da vaga (HTML é limpo automaticamente)...")
        self.txtVaga.setMinimumHeight(150)
        layout.addWidget(self.txtVaga)

        acoes = QHBoxLayout()
        self.btnComparar = QPushButton("Comparar currículo")
        self.btnComparar.setMinimumHeight(42)
        self.btnComparar.clicked.connect(self.comparar)
        self.btn_docx = QPushButton("Exportar DOCX")
        self.btn_pdf = QPushButton("Exportar PDF")
        self.btn_docx.clicked.connect(self.exportar_docx)
        self.btn_pdf.clicked.connect(self.exportar_pdf)
        self.btn_curriculo_docx = QPushButton("Pré-visualizar e editar currículo direcionado")
        self.btn_curriculo_pdf = QPushButton("Gerar currículo adaptado (PDF)")
        self.btn_curriculo_docx.clicked.connect(self.abrir_previa_curriculo)
        self.btn_curriculo_pdf.clicked.connect(self.abrir_previa_curriculo)
        self.btn_curriculo_pdf.hide()
        for botao in (self.btn_docx, self.btn_pdf, self.btn_curriculo_docx, self.btn_curriculo_pdf):
            botao.setProperty("secondary", True)
        self.btn_docx.setEnabled(False)
        self.btn_pdf.setEnabled(False)
        self.btn_curriculo_docx.setEnabled(False)
        self.btn_curriculo_pdf.setEnabled(False)
        acoes.addWidget(self.btnComparar)
        acoes.addWidget(self.btn_docx)
        acoes.addWidget(self.btn_pdf)
        acoes.addStretch()
        layout.addLayout(acoes)
        adaptacao = QHBoxLayout()
        adaptacao.addWidget(self.btn_curriculo_docx)
        adaptacao.addWidget(self.btn_curriculo_pdf)
        adaptacao.addStretch()
        layout.addLayout(adaptacao)

        self.condicoes_match = QComboBox()
        self.condicoes_match.addItem("Condições ainda não verificadas", "pendentes")
        self.condicoes_match.addItem("Escopo, requisitos essenciais e condições validados por mim", "alinhadas")
        self.condicoes_match.addItem("Incompatibilidade essencial confirmada por mim", "incompativeis")
        self.evidencia_match = QLineEdit()
        self.evidencia_match.setPlaceholderText("Evidência da revisão: fonte, data e condição verificada")
        self.lacunas_match = QLineEdit()
        self.lacunas_match.setPlaceholderText("Lacunas confirmadas por você, separadas por ; (opcional)")
        self.txtVaga.textChanged.connect(self._limpar_revisao)
        layout.addWidget(self.condicoes_match)
        layout.addWidget(self.evidencia_match)
        layout.addWidget(self.lacunas_match)
        self.status = QLabel("")
        layout.addWidget(self.status)
        self.score = ScoreCard("Cobertura dos requisitos identificados")
        self.explicacao = SectionCard("Como a nota foi calculada")
        self.encontradas = SectionCard("Competências encontradas")
        self.faltantes = SectionCard("Lacunas confirmadas")
        self.pendentes = SectionCard("Competências não informadas / a validar")
        self.decisao = SectionCard("Recomendação e próximo passo")
        self.abrangencia = SectionCard("Obrigatórios, desejáveis e condições — abrangência")
        self.recomendacoes = SectionCard("Recomendações")
        for card in (self.score, self.explicacao, self.encontradas, self.faltantes, self.pendentes, self.decisao, self.abrangencia, self.recomendacoes):
            card.hide()
            layout.addWidget(card)

        historico_titulo = QLabel("Histórico de comparações")
        historico_titulo.setObjectName("sectionTitle")
        layout.addWidget(historico_titulo)
        self.historico = QTableWidget(0, 3)
        self.historico.setHorizontalHeaderLabels(["Data", "Currículo", "Match"])
        self.historico.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.historico.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.historico.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.historico.setMaximumHeight(180)
        self.historico.cellDoubleClicked.connect(self.abrir_historico)
        layout.addWidget(self.historico)
        self.carregar_historico()
        self.carregar_curriculo_ativo()

    def carregar_curriculo_ativo(self):
        analise = self.db.obter_analise_ativa()
        if not analise:
            self.perfil_ativo.setText("Nenhum currículo analisado. Importe um currículo em “Meu currículo” para ativar a busca personalizada.")
            self.btnBuscarPerfil.setEnabled(False)
            return
        service = JobSearchService()
        try:
            recomendacao = service.recomendacao_para_curriculo()
        except ValueError:
            recomendacao = {"principal": analise["cargo"] or "competências do currículo", "titulos": [], "palavras_chave": []}
        finally:
            service.db.close()
        skills = [item.strip() for item in (analise["hard_skills"] or "").split(";") if item.strip()]
        destaque = ", ".join(skills[:6]) or "competências não identificadas"
        titulos = " · ".join(recomendacao["titulos"][:4]) or recomendacao["principal"]
        comprovadas = ", ".join(recomendacao.get("competencias_comprovadas", [])[:10]) or destaque
        sugeridas = ", ".join(recomendacao.get("palavras_sugeridas", [])[:8]) or "Nenhuma sugestão adicional"
        self.perfil_ativo.setText(
            f"<b>Currículo ativo:</b> {escape(analise['nome_arquivo'])} &nbsp; | &nbsp; "
            f"<b>Perfil:</b> {escape(analise['cargo'] or 'Não identificado')} &nbsp; | &nbsp; "
            f"<b>Busca recomendada (Brasil):</b> {escape(recomendacao['principal'])}<br>"
            f"<b>Títulos relacionados:</b> {escape(titulos)}<br>"
            f"<b>Competências comprovadas:</b> {escape(comprovadas)}<br>"
            f"<b>Termos sugeridos para pesquisar (não comprovam experiência):</b> {escape(sugeridas)}"
        )
        self.btnBuscarPerfil.setEnabled(True)

    def comparar(self):
        if self.thread:
            return
        vaga = self.txtVaga.toPlainText().strip()
        if not vaga:
            QMessageBox.warning(self, "Job Match", "Cole a descrição da vaga.")
            return
        self.btnComparar.setEnabled(False)
        self.status.setText("Analisando compatibilidade em segundo plano...")
        self.thread = QThread(self)
        self.worker = JobMatchWorker(vaga, self.titulo_vaga_atual, {
            "condicoes": self.condicoes_match.currentData(),
            "evidencia": self.evidencia_match.text().strip(),
            "lacunas_confirmadas": [item.strip() for item in self.lacunas_match.text().split(";") if item.strip()],
        })
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.mostrar_resultado)
        self.worker.failed.connect(self.mostrar_erro)
        self.worker.finished.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.thread.finished.connect(self.finalizar_processamento)
        self.thread.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def buscar_vagas(self):
        termo = self.txtBusca.text().strip()
        if not termo:
            QMessageBox.information(self, "Busca de vagas", "Informe um cargo, área ou competência.")
            return
        if self.search_thread:
            return
        self.iniciar_busca(termo, False)

    def buscar_para_curriculo(self, silencioso=False):
        self.carregar_curriculo_ativo()
        if not self.db.obter_analise_ativa():
            return
        try:
            service = JobSearchService()
            try:
                self.txtBusca.setText(service.termo_para_curriculo())
            finally:
                service.db.close()
        except ValueError as erro:
            if not silencioso:
                QMessageBox.information(self, "Busca de vagas", str(erro))
            return
        self.busca_silenciosa = silencioso
        self.iniciar_busca(None, True)

    def iniciar_busca(self, termo, para_curriculo):
        if self.search_thread:
            return
        self.btnBuscar.setEnabled(False)
        self.btnBuscarPerfil.setEnabled(False)
        local = self.cmbEstado.currentText()
        if self.txtCidade.text().strip():
            local = f"{self.txtCidade.text().strip()}, {local}"
        self.status.setText(f"Buscando vagas no Brasil ({local})...")
        self.search_thread = QThread(self)
        self.search_worker = JobSearchWorker(
            termo, para_curriculo, self.cmbEstado.currentData(), self.txtCidade.text().strip(),
            self.cmbModalidade.currentData(), self.cmbSenioridade.currentData(),
        )
        self.search_worker.moveToThread(self.search_thread)
        self.search_thread.started.connect(self.search_worker.run)
        self.search_worker.finished.connect(self.mostrar_vagas_encontradas)
        self.search_worker.failed.connect(self.mostrar_erro_busca)
        self.search_worker.finished.connect(self.search_thread.quit)
        self.search_worker.failed.connect(self.search_thread.quit)
        self.search_thread.finished.connect(self.finalizar_busca)
        self.search_thread.finished.connect(self.search_worker.deleteLater)
        self.search_thread.finished.connect(self.search_thread.deleteLater)
        self.search_thread.start()

    def mostrar_vagas_encontradas(self, vagas):
        self.vagas_encontradas = vagas
        self.resultados_busca.setRowCount(len(vagas))
        for linha, vaga in enumerate(vagas):
            self.resultados_busca.setItem(linha, 0, QTableWidgetItem(vaga["titulo"]))
            self.resultados_busca.setItem(linha, 1, QTableWidgetItem(vaga["empresa"]))
            self.resultados_busca.setItem(linha, 2, QTableWidgetItem(vaga["localizacao"]))
            self.resultados_busca.setItem(linha, 3, QTableWidgetItem(vaga["fonte"]))
            ranking = QTableWidgetItem(f"{vaga.get('rank_score', 0)}%")
            ranking.setToolTip(vaga.get("rank_explanation", "Ranking calculado pelo perfil e filtros."))
            self.resultados_busca.setItem(linha, 4, ranking)
            self.resultados_busca.setItem(linha, 5, QTableWidgetItem(vaga.get("decision", "nova").title()))
            self.resultados_busca.setItem(linha, 6, QTableWidgetItem("Pendente"))
        self.btnCompararTodas.setEnabled(bool(vagas))
        self._mostrar_metricas_fontes()
        if not vagas:
            self.status.setText(
                "Nenhuma vaga no Brasil encontrada nas fontes públicas integradas para esse filtro. "
                "Use a Central de Carreira para pesquisar LinkedIn, Gupy, Indeed, Catho e Vagas.com no navegador."
            )
        else:
            self.status.setText(
                f"{len(vagas)} vagas únicas encontradas e ordenadas pelo seu perfil. "
                "Você pode favoritar, descartar ou criar uma candidatura."
            )

    def _mostrar_metricas_fontes(self):
        summary = self.db.resumo_ultima_busca()
        if not summary:
            self.resumo_fontes.setText("Nenhuma métrica de busca disponível.")
            return
        parts = []
        for metric in summary["providers"]:
            received = metric["received"] or 0
            eligible = metric["eligible_brazil"] or 0
            filtered = max(0, received - eligible)
            status = "falhou" if metric["error"] else f"{metric['duration_ms']} ms"
            parts.append(
                f"<b>{metric['provider']}</b>: {received} recebidas, {eligible} Brasil, "
                f"{filtered} filtradas ({status})"
            )
        text = " &nbsp; • &nbsp; ".join(parts) or "Nenhum provedor habilitado respondeu."
        self.resumo_fontes.setText(
            f"{text}<br><b>Exibidas:</b> {summary['search']['result_count']} &nbsp; • &nbsp; "
            f"<b>Descartadas pelo usuário:</b> {summary['discarded']}"
        )

    def _vaga_selecionada(self):
        linha = self.resultados_busca.currentRow()
        if linha < 0 or linha >= len(self.vagas_encontradas):
            QMessageBox.information(self, "Vagas", "Selecione uma vaga na lista.")
            return None, -1
        return self.vagas_encontradas[linha], linha

    def favoritar_vaga(self):
        vaga, linha = self._vaga_selecionada()
        if not vaga:
            return
        self.db.definir_decisao_vaga(vaga["id"], "favorita")
        vaga["decision"] = "favorita"
        self.resultados_busca.setItem(linha, 5, QTableWidgetItem("Favorita"))
        self.status.setText("Vaga adicionada aos favoritos.")

    def descartar_vaga(self):
        vaga, linha = self._vaga_selecionada()
        if not vaga:
            return
        self.db.definir_decisao_vaga(vaga["id"], "descartada")
        self.vagas_encontradas.pop(linha)
        self.resultados_busca.removeRow(linha)
        self._mostrar_metricas_fontes()
        self.status.setText("Vaga descartada. Ela não aparecerá novamente nas próximas buscas.")

    def converter_em_candidatura(self):
        vaga, linha = self._vaga_selecionada()
        if not vaga:
            return
        candidatura_id = self.db.converter_vaga_em_candidatura(vaga["id"])
        vaga["decision"] = "candidatura"
        self.resultados_busca.setItem(linha, 5, QTableWidgetItem("Candidatura"))
        janela = self.window()
        if hasattr(janela, "career_hub_page"):
            janela.career_hub_page.carregar_oportunidades()
        self.status.setText(
            f"Candidatura #{candidatura_id} criada. Acompanhe as próximas ações na Central de Carreira."
        )

    def usar_vaga_selecionada(self, linha, _coluna):
        vaga = self.vagas_encontradas[linha]
        self.titulo_vaga_atual = vaga["titulo"]
        self.txtVaga.setPlainText(vaga["descricao"])
        self.status.setText(f"Comparando a vaga selecionada: {vaga['titulo']}...")
        self.comparar()

    def abrir_vaga_selecionada(self):
        linha = self.resultados_busca.currentRow()
        if linha < 0:
            QMessageBox.information(self, "Abrir vaga", "Selecione uma vaga na lista.")
            return
        url = self.vagas_encontradas[linha].get("url")
        target = QUrl(url or "")
        if target.scheme().casefold() not in {"http", "https"}:
            QMessageBox.warning(self, "Abrir vaga", "O link da vaga não é HTTP/HTTPS válido.")
            return
        QDesktopServices.openUrl(target)

    def abrir_pesquisa_externa(self, fonte):
        """Abre uma busca pública já limitada ao cargo e local selecionados."""
        termo = self.txtBusca.text().strip()
        if not termo:
            try:
                service = JobSearchService()
                try:
                    termo = service.termo_para_curriculo()
                finally:
                    service.db.close()
                self.txtBusca.setText(termo)
            except ValueError:
                QMessageBox.information(self, "Busca de vagas", "Informe um cargo ou analise um currículo antes de pesquisar.")
                return
        local = self.txtCidade.text().strip()
        estado = self.cmbEstado.currentData()
        if estado:
            local = ", ".join(parte for parte in (local, estado, "Brasil") if parte)
        else:
            local = ", ".join(parte for parte in (local, "Brasil") if parte)
        consulta = quote_plus(f"{termo} vagas {local}")
        urls = {
            "Google": f"https://www.google.com/search?q={consulta}",
            "LinkedIn": f"https://www.linkedin.com/jobs/search/?keywords={quote_plus(termo)}&location={quote_plus(local)}",
            "Indeed": f"https://br.indeed.com/jobs?q={quote_plus(termo)}&l={quote_plus(local)}",
            "Gupy": f"https://www.google.com/search?q=site%3Agupy.io%2Fjobs+{consulta}",
        }
        QDesktopServices.openUrl(QUrl(urls[fonte]))
        self.status.setText(f"Pesquisa aberta em {fonte} para: {termo} — {local}.")

    def mostrar_erro_busca(self, mensagem):
        self.status.setText(f"Não foi possível atualizar vagas recomendadas: {mensagem}")
        if not self.busca_silenciosa:
            QMessageBox.critical(self, "Erro na busca de vagas", mensagem)

    def finalizar_busca(self):
        self.btnBuscar.setEnabled(True)
        self.btnBuscarPerfil.setEnabled(True)
        self.search_thread = None
        self.search_worker = None
        self.busca_silenciosa = False

    def comparar_todas(self):
        if not self.vagas_encontradas or self.batch_thread:
            return
        self.btnCompararTodas.setEnabled(False)
        self.btnCancelarLote.setEnabled(True)
        self.btnComparar.setEnabled(False)
        self.status.setText(f"Comparando 0 de {len(self.vagas_encontradas)} vagas...")
        self.batch_thread = QThread(self)
        self.batch_worker = JobBatchMatchWorker(self.vagas_encontradas)
        self.batch_worker.moveToThread(self.batch_thread)
        self.batch_thread.started.connect(self.batch_worker.run)
        self.batch_worker.progress.connect(self.atualizar_progresso_lote)
        self.batch_worker.finished.connect(self.finalizar_lote)
        self.batch_worker.failed.connect(self.mostrar_erro_lote)
        self.batch_worker.finished.connect(self.batch_thread.quit)
        self.batch_worker.failed.connect(self.batch_thread.quit)
        self.batch_thread.finished.connect(self.limpar_lote)
        self.batch_thread.finished.connect(self.batch_worker.deleteLater)
        self.batch_thread.finished.connect(self.batch_thread.deleteLater)
        self.batch_thread.start()

    def atualizar_progresso_lote(self, indice, total, nota, erro):
        self.resultados_busca.setItem(indice, 6, QTableWidgetItem(f"{nota}%" if nota >= 0 else ("Falhou" if erro else "Pendente")))
        self.status.setText(f"Comparando {indice + 1} de {total} vagas...")

    def finalizar_lote(self, resultados):
        self.status.setText(f"{len(resultados)} vagas comparadas e salvas no histórico.")
        if resultados:
            self.mostrar_resultado(max(resultados, key=lambda item: item["compatibilidade"] if item["compatibilidade"] is not None else -1))

    def mostrar_erro_lote(self, mensagem):
        QMessageBox.critical(self, "Erro ao comparar vagas", mensagem)

    def limpar_lote(self):
        self.btnCompararTodas.setEnabled(bool(self.vagas_encontradas))
        self.btnComparar.setEnabled(True)
        self.btnCancelarLote.setEnabled(False)
        self.batch_thread = None
        self.batch_worker = None

    def cancelar_lote(self):
        if self.batch_thread:
            self.batch_thread.requestInterruption()
            self.status.setText("Cancelamento solicitado; finalizando a vaga em andamento...")

    def shutdown(self):
        """Interrompe buscas e comparações ainda ativas durante a saída."""
        shutdown_threads((self.thread, self.search_thread, self.batch_thread))

    def finalizar_processamento(self):
        self.btnComparar.setEnabled(True)
        self.status.setText("")
        self.thread = None
        self.worker = None

    def mostrar_erro(self, mensagem):
        QMessageBox.critical(self, "Erro no Job Match", mensagem)

    def mostrar_resultado(self, resultado):
        self.resultado_atual = resultado
        self.score.setScore(resultado["compatibilidade"])
        self.score.show()
        self.pendentes.setItems(resultado.get("competencias_nao_informadas", []))
        self.abrangencia.setItems(resultado.get("abrangencia", ["Inventário não registrado; refaça a comparação."]))
        self.decisao.setText(
            f"{resultado.get('recomendacao', 'investigar').capitalize()}: "
            f"{resultado.get('justificativa', 'Registro anterior aos critérios atuais; refaça a comparação.')} "
            f"Próximo passo: {resultado.get('proximo_passo', 'Refazer a comparação.')}"
        )
        for card in (self.explicacao, self.encontradas, self.faltantes, self.pendentes, self.decisao, self.abrangencia, self.recomendacoes):
            card.show()
        self.explicacao.setText(resultado["explicacao"])
        self.encontradas.setItems(resultado.get("evidencias") or resultado["competencias_encontradas"])
        self.faltantes.setItems(resultado["competencias_faltantes"])
        self.recomendacoes.setItems(resultado["recomendacoes"])
        self.btn_docx.setEnabled(True)
        self.btn_pdf.setEnabled(True)
        self.btn_curriculo_docx.setEnabled(True)
        self.btn_curriculo_pdf.setEnabled(True)
        self.carregar_historico()

    def carregar_historico(self):
        dados = self.db.listar_job_matches()
        self.historico.setRowCount(len(dados))
        for linha, item in enumerate(dados):
            data = str(item["created_at"])[:16]
            primeira = QTableWidgetItem(data)
            primeira.setData(256, item["id"])
            self.historico.setItem(linha, 0, primeira)
            self.historico.setItem(linha, 1, QTableWidgetItem(item["nome_arquivo"]))
            self.historico.setItem(linha, 2, QTableWidgetItem(f'{item["compatibilidade"]}%' if item["compatibilidade"] >= 0 else "Pendente"))

    def abrir_historico(self, linha, _coluna):
        match_id = self.historico.item(linha, 0).data(256)
        item = self.db.obter_job_match(match_id)
        if not item:
            return
        stored = json.loads(item["resultado_json"] or "{}")
        if stored:
            stored.update(id=item["id"], descricao_vaga=item["descricao"], curriculo=item["nome_arquivo"])
            self.mostrar_resultado(stored)
            return
        self.mostrar_resultado({
            "id": item["id"], "compatibilidade": None,
            "competencias_encontradas": json.loads(item["competencias_encontradas"]),
            "competencias_faltantes": [],
            "competencias_nao_informadas": json.loads(item["competencias_faltantes"]),
            "recomendacoes": json.loads(item["recomendacoes"]),
            "explicacao": f"Registro legado (nota original: {item['compatibilidade']}%). Refazer com os critérios atuais. " + (item["explicacao"] or ""), "resumo": item["resumo"] or "",
            "descricao_vaga": item["descricao"], "curriculo": item["nome_arquivo"],
        })

    def exportar_docx(self):
        try:
            destino = self.relatorios.exportar_job_match_docx(self.resultado_atual)
            QMessageBox.information(self, "Relatório criado", f"DOCX salvo em:\n{destino.resolve()}")
        except Exception as erro:
            QMessageBox.critical(self, "Erro ao exportar DOCX", str(erro))

    def exportar_pdf(self):
        destino, _ = QFileDialog.getSaveFileName(self, "Salvar relatório PDF", "job_match.pdf", "PDF (*.pdf)")
        if not destino:
            return
        try:
            self.relatorios.exportar_job_match_pdf(self.resultado_atual, destino)
            QMessageBox.information(self, "Relatório criado", f"PDF salvo em:\n{destino}")
        except Exception as erro:
            QMessageBox.critical(self, "Erro ao exportar PDF", str(erro))

    def _preparar_curriculo_adaptado(self):
        service = ResumeAdaptationService()
        try:
            self.curriculo_adaptado = service.preparar(
                self.txtVaga.toPlainText(), self.titulo_vaga_atual,
            )
        finally:
            service.db.close()
        return self.curriculo_adaptado

    def abrir_previa_curriculo(self):
        try:
            dados = self._preparar_curriculo_adaptado()
            dialog = ResumePreviewDialog(dados, self.relatorios, self)
            dialog.exec()
        except Exception as erro:
            QMessageBox.critical(self, "Currículo direcionado", str(erro))

    def exportar_curriculo_adaptado_docx(self):
        try:
            dados = self._preparar_curriculo_adaptado()
            destino = self.relatorios.exportar_curriculo_adaptado_docx(dados)
            QMessageBox.information(
                self, "Currículo adaptado",
                f"Versão revisável salva em:\n{destino.resolve()}\n\nO currículo original não foi alterado.",
            )
        except Exception as erro:
            QMessageBox.critical(self, "Currículo adaptado", str(erro))

    def exportar_curriculo_adaptado_pdf(self):
        destino, _ = QFileDialog.getSaveFileName(self, "Salvar currículo adaptado", "curriculo_direcionado.pdf", "PDF (*.pdf)")
        if not destino:
            return
        try:
            dados = self._preparar_curriculo_adaptado()
            self.relatorios.exportar_curriculo_adaptado_pdf(dados, destino)
            QMessageBox.information(self, "Currículo adaptado", f"PDF salvo em:\n{destino}")
        except Exception as erro:
            QMessageBox.critical(self, "Currículo adaptado", str(erro))


    def _limpar_revisao(self):
        self.condicoes_match.setCurrentIndex(0)
        self.evidencia_match.clear()
        self.lacunas_match.clear()

import json
import textwrap
from urllib.parse import quote_plus

from PySide6.QtCore import QThread, QUrl
from PySide6.QtGui import QPainter, QPdfWriter, QPageSize, QDesktopServices
from PySide6.QtWidgets import (
    QWidget, QLabel, QTextEdit, QPushButton, QVBoxLayout, QHBoxLayout,
    QMessageBox, QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QLineEdit, QComboBox, QScrollArea, QFrame,
)

from app.database.sqlite_db import Database
from app.services.report_service import ReportService
from app.services.job_search_service import JobSearchService
from app.services.resume_adaptation_service import ResumeAdaptationService
from app.ui.widgets.score_card import ScoreCard
from app.ui.widgets.section_card import SectionCard
from app.ui.workers import JobMatchWorker, JobSearchWorker, JobBatchMatchWorker


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
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        titulo = QLabel("Job Match")
        titulo.setStyleSheet("font-size:28px;font-weight:bold;color:#1976D2;")
        layout.addWidget(titulo)
        self.perfil_ativo = QLabel()
        self.perfil_ativo.setWordWrap(True)
        self.perfil_ativo.setStyleSheet("background:#EAF3FF;border:1px solid #C9DDF7;border-radius:10px;padding:12px;color:#174EA6;font-size:13px;")
        layout.addWidget(self.perfil_ativo)
        layout.addWidget(QLabel("Buscar vagas remotas automaticamente"))
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
        self.btnAbrirVaga = QPushButton("Abrir vaga selecionada")
        self.btnAbrirVaga.clicked.connect(self.abrir_vaga_selecionada)
        busca.addWidget(self.txtBusca)
        busca.addWidget(self.cmbEstado)
        busca.addWidget(self.txtCidade)
        busca.addWidget(self.btnBuscar)
        busca.addWidget(self.btnBuscarPerfil)
        busca.addWidget(self.btnGoogle)
        busca.addWidget(self.btnLinkedIn)
        busca.addWidget(self.btnIndeed)
        busca.addWidget(self.btnAbrirVaga)
        layout.addLayout(busca)
        self.resultados_busca = QTableWidget(0, 5)
        self.resultados_busca.setHorizontalHeaderLabels(["Vaga", "Empresa", "Localização", "Fonte", "Match"])
        self.resultados_busca.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.resultados_busca.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.resultados_busca.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.resultados_busca.setMaximumHeight(190)
        self.resultados_busca.cellDoubleClicked.connect(self.usar_vaga_selecionada)
        layout.addWidget(self.resultados_busca)
        self.btnCompararTodas = QPushButton("Comparar todas as vagas encontradas")
        self.btnCompararTodas.setEnabled(False)
        self.btnCompararTodas.clicked.connect(self.comparar_todas)
        layout.addWidget(self.btnCompararTodas)
        self.btnCancelarLote = QPushButton("Cancelar comparação em lote")
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
        self.btn_curriculo_docx = QPushButton("Gerar currículo adaptado (DOCX)")
        self.btn_curriculo_pdf = QPushButton("Gerar currículo adaptado (PDF)")
        self.btn_curriculo_docx.clicked.connect(self.exportar_curriculo_adaptado_docx)
        self.btn_curriculo_pdf.clicked.connect(self.exportar_curriculo_adaptado_pdf)
        self.btn_docx.setEnabled(False)
        self.btn_pdf.setEnabled(False)
        self.btn_curriculo_docx.setEnabled(False)
        self.btn_curriculo_pdf.setEnabled(False)
        acoes.addWidget(self.btnComparar)
        acoes.addWidget(self.btn_docx)
        acoes.addWidget(self.btn_pdf)
        acoes.addWidget(self.btn_curriculo_docx)
        acoes.addWidget(self.btn_curriculo_pdf)
        acoes.addStretch()
        layout.addLayout(acoes)

        self.status = QLabel("")
        layout.addWidget(self.status)
        self.score = ScoreCard("Compatibilidade")
        self.explicacao = SectionCard("Como a nota foi calculada")
        self.encontradas = SectionCard("Competências encontradas")
        self.faltantes = SectionCard("Competências faltantes")
        self.recomendacoes = SectionCard("Recomendações")
        for card in (self.score, self.explicacao, self.encontradas, self.faltantes, self.recomendacoes):
            card.hide()
            layout.addWidget(card)

        historico_titulo = QLabel("Histórico de comparações")
        historico_titulo.setStyleSheet("font-size:16px;font-weight:bold;color:#1976D2;margin-top:8px;")
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
        analise = self.db.obter_ultima_analise()
        if not analise:
            self.perfil_ativo.setText("Nenhum currículo analisado. Importe um currículo em “Meu currículo” para ativar a busca personalizada.")
            self.btnBuscarPerfil.setEnabled(False)
            return
        try:
            recomendacao = JobSearchService().recomendacao_para_curriculo()
        except ValueError:
            recomendacao = {"principal": analise["cargo"] or "competências do currículo", "titulos": [], "palavras_chave": []}
        skills = [item.strip() for item in (analise["hard_skills"] or "").split(";") if item.strip()]
        destaque = ", ".join(skills[:6]) or "competências não identificadas"
        titulos = " · ".join(recomendacao["titulos"][:4]) or recomendacao["principal"]
        palavras = ", ".join(recomendacao["palavras_chave"][:10]) or destaque
        self.perfil_ativo.setText(
            f"<b>Currículo ativo:</b> {analise['nome_arquivo']} &nbsp; | &nbsp; "
            f"<b>Perfil:</b> {analise['cargo'] or 'Não identificado'} &nbsp; | &nbsp; "
            f"<b>Busca recomendada (Brasil):</b> {recomendacao['principal']}<br>"
            f"<b>Títulos relacionados:</b> {titulos}<br>"
            f"<b>Palavras-chave para a vaga:</b> {palavras}"
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
        self.worker = JobMatchWorker(vaga, self.titulo_vaga_atual)
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
        if not self.db.obter_ultima_analise():
            return
        try:
            self.txtBusca.setText(JobSearchService().termo_para_curriculo())
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
        self.search_worker = JobSearchWorker(termo, para_curriculo, self.cmbEstado.currentData(), self.txtCidade.text().strip())
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
            self.resultados_busca.setItem(linha, 4, QTableWidgetItem("Pendente"))
        self.btnCompararTodas.setEnabled(bool(vagas))
        if not vagas:
            self.status.setText(
                "Nenhuma vaga no Brasil encontrada nas fontes públicas integradas para esse filtro. "
                "Use a Central de Carreira para pesquisar LinkedIn, Gupy, Indeed, Catho e Vagas.com no navegador."
            )
        else:
            self.status.setText("Selecione uma vaga para carregar e comparar.")

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
        if url:
            QDesktopServices.openUrl(QUrl(url))

    def abrir_pesquisa_externa(self, fonte):
        """Abre uma busca pública já limitada ao cargo e local selecionados."""
        termo = self.txtBusca.text().strip()
        if not termo:
            try:
                termo = JobSearchService().termo_para_curriculo()
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
        self.resultados_busca.setItem(indice, 4, QTableWidgetItem(f"{nota}%" if nota >= 0 else "Falhou"))
        self.status.setText(f"Comparando {indice + 1} de {total} vagas...")

    def finalizar_lote(self, resultados):
        self.status.setText(f"{len(resultados)} vagas comparadas e salvas no histórico.")
        if resultados:
            self.mostrar_resultado(max(resultados, key=lambda item: item["compatibilidade"]))

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
        self.explicacao.setText(resultado["explicacao"])
        self.encontradas.setItems(resultado["competencias_encontradas"])
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
            self.historico.setItem(linha, 2, QTableWidgetItem(f'{item["compatibilidade"]}%'))

    def abrir_historico(self, linha, _coluna):
        match_id = self.historico.item(linha, 0).data(256)
        item = self.db.obter_job_match(match_id)
        if not item:
            return
        self.mostrar_resultado({
            "id": item["id"], "compatibilidade": item["compatibilidade"],
            "competencias_encontradas": json.loads(item["competencias_encontradas"]),
            "competencias_faltantes": json.loads(item["competencias_faltantes"]),
            "recomendacoes": json.loads(item["recomendacoes"]),
            "explicacao": item["explicacao"] or "", "resumo": item["resumo"] or "",
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
            writer = QPdfWriter(destino)
            writer.setPageSize(QPageSize(QPageSize.A4))
            writer.setResolution(96)
            painter = QPainter(writer)
            painter.setFont(self.font())
            y, margem, largura = 70, 55, 80
            def escrever(texto, destaque=False):
                nonlocal y
                painter.setFont(self.font())
                fonte = painter.font(); fonte.setBold(destaque); painter.setFont(fonte)
                for linha in textwrap.wrap(str(texto), width=largura) or [""]:
                    if y > 1080:
                        writer.newPage(); y = 70
                    painter.drawText(margem, y, linha); y += 20
                y += 8
            escrever("Relatório de Job Match", True)
            escrever(f"Compatibilidade: {self.resultado_atual['compatibilidade']}%", True)
            escrever("Como a nota foi calculada", True); escrever(self.resultado_atual.get("explicacao", ""))
            for titulo, chave in (("Competências encontradas", "competencias_encontradas"), ("Competências faltantes", "competencias_faltantes"), ("Recomendações", "recomendacoes")):
                escrever(titulo, True)
                for item in self.resultado_atual.get(chave, []): escrever("• " + item)
            painter.end()
            QMessageBox.information(self, "Relatório criado", f"PDF salvo em:\n{destino}")
        except Exception as erro:
            QMessageBox.critical(self, "Erro ao exportar PDF", str(erro))

    def _preparar_curriculo_adaptado(self):
        self.curriculo_adaptado = ResumeAdaptationService().preparar(
            self.txtVaga.toPlainText(), self.titulo_vaga_atual,
        )
        return self.curriculo_adaptado

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

import re
from datetime import datetime
from html import escape
from urllib.parse import quote_plus

from PySide6.QtCore import Qt, QThread, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QComboBox,
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
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.database.sqlite_db import Database
from app.services.job_search_service import JobSearchService
from app.services.report_service import ReportService
from app.ui.workers import CareerWorker, shutdown_threads


class CareerHubPage(QWidget):
    """Central V2: oportunidades salvas, mentor de carreira e treino de entrevista."""

    busca_integrada_solicitada = Signal()
    STATUS_CANDIDATURA = [
        "Salva", "Preparando candidatura", "Candidatado", "Triagem",
        "Entrevista com RH", "Entrevista técnica", "Proposta", "Rejeitado", "Encerrado",
    ]

    def __init__(self):
        super().__init__()
        self.db = Database()
        self.relatorios = ReportService()
        self.thread = self.worker = None
        self.pergunta_atual = ""
        self.pacote_atual = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        titulo = QLabel("Central de Carreira")
        titulo.setObjectName("pageTitle")
        layout.addWidget(titulo)
        self.perfil_resumo = QLabel()
        self.perfil_resumo.setWordWrap(True)
        self.perfil_resumo.setTextFormat(Qt.RichText)
        self.perfil_resumo.setObjectName("profileBanner")
        layout.addWidget(self.perfil_resumo)
        abas = QTabWidget()
        abas.addTab(self._aba_oportunidades(), "Candidaturas")
        abas.addTab(self._aba_chat(), "Assistente")
        abas.addTab(self._aba_entrevista(), "Simulador")
        abas.addTab(self._aba_plano(), "Plano de ação")
        abas.addTab(self._aba_estudio(), "Estúdio V3")
        layout.addWidget(abas)
        self.carregar_oportunidades()
        self.atualizar_perfil()

    def _aba_oportunidades(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        aba = QWidget(); layout = QVBoxLayout(aba)
        scroll.setWidget(aba)
        instrucao = QLabel(
            "Use a busca integrada para vagas públicas. Nas plataformas que exigem conta, "
            "a pesquisa é aberta no seu navegador para que você entre com seu próprio login."
        )
        instrucao.setWordWrap(True)
        instrucao.setObjectName("mutedText")
        layout.addWidget(instrucao)
        self.pipeline_resumo = QLabel()
        self.pipeline_resumo.setObjectName("profileBanner")
        self.pipeline_resumo.setWordWrap(True)
        layout.addWidget(self.pipeline_resumo)
        acoes_busca = QHBoxLayout()
        self.btn_busca_integrada = QPushButton("Buscar vagas para meu currículo")
        self.btn_busca_integrada.clicked.connect(self.busca_integrada_solicitada.emit)
        acoes_busca.addWidget(self.btn_busca_integrada)
        for plataforma in ("LinkedIn", "Gupy", "Indeed", "Catho", "Vagas.com"):
            botao = QPushButton(f"Abrir {plataforma}")
            botao.setProperty("secondary", True)
            botao.clicked.connect(lambda _=False, nome=plataforma: self.abrir_plataforma(nome))
            acoes_busca.addWidget(botao)
        acoes_busca.addStretch()
        layout.addLayout(acoes_busca)
        self.status_busca = QLabel("")
        self.status_busca.setWordWrap(True)
        self.status_busca.setObjectName("mutedText")
        layout.addWidget(self.status_busca)
        linha = QHBoxLayout()
        self.o_titulo = QLineEdit(); self.o_titulo.setPlaceholderText("Título da vaga *")
        self.o_empresa = QLineEdit(); self.o_empresa.setPlaceholderText("Empresa")
        self.o_plataforma = QComboBox(); self.o_plataforma.addItems(
            ["Manual", "Vagas.com", "Greenhouse", "Lever", "LinkedIn", "Gupy", "Indeed", "Catho"]
        )
        linha.addWidget(self.o_titulo, 2); linha.addWidget(self.o_empresa, 2); linha.addWidget(self.o_plataforma, 1)
        layout.addLayout(linha)
        self.o_url = QLineEdit(); self.o_url.setPlaceholderText("Link da vaga (opcional)")
        self.o_descricao = QTextEdit(); self.o_descricao.setPlaceholderText("Descrição ou observações da vaga (opcional)"); self.o_descricao.setMaximumHeight(100)
        detalhes = QHBoxLayout()
        self.o_salario = QLineEdit(); self.o_salario.setPlaceholderText("Faixa salarial")
        self.o_modelo = QComboBox(); self.o_modelo.addItems(["Não informado", "Remoto", "Híbrido", "Presencial"])
        self.o_contrato = QComboBox(); self.o_contrato.addItems(["Não informado", "CLT", "PJ", "Temporário", "Estágio"])
        detalhes.addWidget(self.o_salario); detalhes.addWidget(self.o_modelo); detalhes.addWidget(self.o_contrato)
        contato = QHBoxLayout()
        self.o_recrutador = QLineEdit(); self.o_recrutador.setPlaceholderText("Nome do recrutador")
        self.o_email = QLineEdit(); self.o_email.setPlaceholderText("E-mail do recrutador")
        self.o_telefone = QLineEdit(); self.o_telefone.setPlaceholderText("Telefone")
        contato.addWidget(self.o_recrutador); contato.addWidget(self.o_email); contato.addWidget(self.o_telefone)
        acompanhamento = QHBoxLayout()
        self.o_proxima_acao = QLineEdit(); self.o_proxima_acao.setPlaceholderText("Próxima ação")
        self.o_prazo = QLineEdit(); self.o_prazo.setPlaceholderText("Prazo (AAAA-MM-DD)")
        self.o_data_candidatura = QLineEdit(); self.o_data_candidatura.setPlaceholderText("Candidatura (AAAA-MM-DD)")
        acompanhamento.addWidget(self.o_proxima_acao, 2); acompanhamento.addWidget(self.o_prazo); acompanhamento.addWidget(self.o_data_candidatura)
        self.o_status = QComboBox(); self.o_status.addItems(self.STATUS_CANDIDATURA)
        self.o_salvar = QPushButton("Salvar oportunidade")
        self.o_salvar.clicked.connect(self.salvar_oportunidade)
        self.o_atualizar_status = QPushButton("Atualizar etapa da selecionada")
        self.o_atualizar_status.setProperty("secondary", True)
        self.o_atualizar_status.clicked.connect(self.atualizar_etapa_oportunidade)
        acoes_oportunidade = QHBoxLayout(); acoes_oportunidade.addWidget(self.o_salvar); acoes_oportunidade.addWidget(self.o_atualizar_status); acoes_oportunidade.addStretch()
        layout.addWidget(self.o_url); layout.addLayout(detalhes); layout.addLayout(contato)
        layout.addLayout(acompanhamento); layout.addWidget(self.o_descricao); layout.addWidget(self.o_status); layout.addLayout(acoes_oportunidade)
        self.tabela = QTableWidget(0, 6); self.tabela.setHorizontalHeaderLabels(
            ["Vaga", "Empresa", "Fonte", "Etapa", "Próxima ação", "Atualizada"]
        )
        self.tabela.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tabela.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabela.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabela.cellDoubleClicked.connect(self.abrir_oportunidade_selecionada)
        self.tabela.itemSelectionChanged.connect(self.carregar_historico_selecionado)
        layout.addWidget(self.tabela)
        historico_titulo = QLabel("Histórico da candidatura")
        historico_titulo.setObjectName("sectionTitle")
        self.historico_candidatura = QTableWidget(0, 3)
        self.historico_candidatura.setHorizontalHeaderLabels(["Data", "Mudança", "Observação"])
        self.historico_candidatura.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.historico_candidatura.setMaximumHeight(130)
        layout.addWidget(historico_titulo); layout.addWidget(self.historico_candidatura)
        self.carregar_oportunidades()
        return scroll

    def atualizar_perfil(self):
        """Exibe uma síntese determinística da última análise, sem nova chamada à IA."""
        analise = self.db.obter_analise_ativa()
        if not analise:
            self.perfil_resumo.setText(
                "<b>Seu perfil ainda não está ativo.</b> Importe e analise um currículo em “Meu currículo” "
                "para receber diagnóstico, títulos recomendados e buscas personalizadas."
            )
            if hasattr(self, "btn_busca_integrada"):
                self.btn_busca_integrada.setEnabled(False)
            return
        service = JobSearchService()
        try:
            recomendacao = service.recomendacao_para_curriculo()
        finally:
            service.db.close()
        habilidades = [x.strip() for x in (analise["hard_skills"] or "").split(";") if x.strip()]
        faltantes = [x.strip() for x in (analise["competencias_faltantes"] or "").split(";") if x.strip()]
        titulos = " · ".join(recomendacao["titulos"][:4])
        comprovadas = ", ".join(recomendacao.get("competencias_comprovadas", [])[:10])
        sugeridas = ", ".join(recomendacao.get("palavras_sugeridas", [])[:8])
        self.perfil_resumo.setText(
            f"<b>Perfil ativo:</b> {escape(analise['cargo'] or 'Não identificado')} &nbsp; | &nbsp; "
            f"<b>Área:</b> {escape(analise['area'] or 'Não identificada')} &nbsp; | &nbsp; "
            f"<b>Qualidade ATS estimada:</b> {analise['ats_score'] or 0}%<br>"
            f"<b>Busca recomendada (Brasil):</b> {escape(recomendacao['principal'])}<br>"
            f"<b>Títulos relacionados:</b> {escape(titulos)}<br>"
            f"<b>Competências identificadas:</b> {escape(', '.join(habilidades[:8]) or 'Não identificadas')}<br>"
            f"<b>Competências comprovadas:</b> {escape(comprovadas or 'Não identificadas')}<br>"
            f"<b>Termos de mercado sugeridos:</b> {escape(sugeridas or 'Nenhuma sugestão adicional')}<br>"
            f"<b>Para desenvolver:</b> {escape(', '.join(faltantes[:4]) or 'Revise as recomendações da análise')}"
        )
        if hasattr(self, "btn_busca_integrada"):
            self.btn_busca_integrada.setEnabled(True)

    def abrir_plataforma(self, plataforma):
        """Abre uma pesquisa oficial sem tentar acessar áreas privadas do candidato."""
        try:
            service = JobSearchService()
            try:
                consulta = service.termo_para_curriculo()
            finally:
                service.db.close()
        except ValueError:
            QMessageBox.information(self, "Busca de vagas", "Analise um currículo antes de pesquisar vagas.")
            return
        termo = quote_plus(consulta)
        urls = {
            "LinkedIn": f"https://www.linkedin.com/jobs/search/?keywords={termo}&location=Brasil",
            "Gupy": f"https://www.google.com/search?q=site%3Agupy.io%2Fjobs+{termo}",
            "Indeed": f"https://br.indeed.com/jobs?q={termo}",
            "Catho": f"https://www.catho.com.br/vagas/?q={termo}",
            "Vagas.com": f"https://www.google.com/search?q=site%3Avagas.com.br+{termo}",
        }
        QDesktopServices.openUrl(QUrl(urls[plataforma]))
        self.status_busca.setText(
            f"Pesquisa de “{consulta}” aberta em {plataforma}. Faça login, se solicitado, e salve as vagas relevantes nesta Central."
        )

    def _aba_chat(self):
        aba = QWidget(); layout = QVBoxLayout(aba)
        layout.addWidget(QLabel("Pergunte sobre currículo, posicionamento, carreira ou preparação para vagas."))
        self.chat = QTextEdit(); self.chat.setReadOnly(True)
        self.chat.setPlaceholderText("A conversa aparecerá aqui.")
        self.chat_input = QLineEdit(); self.chat_input.setPlaceholderText("Ex.: Como posso melhorar meu currículo para uma vaga de analista?")
        self.chat_enviar = QPushButton("Enviar")
        self.chat_enviar.clicked.connect(lambda: self.iniciar("conversar", [self.chat_input.text()], self.resposta_chat))
        self.chat_input.returnPressed.connect(self.chat_enviar.click)
        layout.addWidget(self.chat); layout.addWidget(self.chat_input); layout.addWidget(self.chat_enviar)
        return aba

    def _aba_entrevista(self):
        aba = QWidget(); layout = QVBoxLayout(aba)
        linha = QHBoxLayout(); self.tema = QComboBox(); self.tema.addItems(["RH", "Técnica", "Comportamental"])
        self.btn_pergunta = QPushButton("Nova pergunta")
        self.btn_pergunta.clicked.connect(lambda: self.iniciar("proxima_pergunta", [self.tema.currentText()], self.mostrar_pergunta))
        linha.addWidget(self.tema); linha.addWidget(self.btn_pergunta); linha.addStretch(); layout.addLayout(linha)
        self.lbl_pergunta = QLabel("Clique em 'Nova pergunta' para iniciar."); self.lbl_pergunta.setWordWrap(True)
        self.resposta = QTextEdit(); self.resposta.setPlaceholderText("Digite sua resposta...")
        self.btn_avaliar = QPushButton("Avaliar resposta")
        self.btn_avaliar.clicked.connect(self.avaliar_resposta)
        self.feedback = QLabel(""); self.feedback.setWordWrap(True)
        layout.addWidget(self.lbl_pergunta); layout.addWidget(self.resposta); layout.addWidget(self.btn_avaliar); layout.addWidget(self.feedback)
        return aba

    def _aba_plano(self):
        aba = QWidget(); layout = QVBoxLayout(aba)
        self.plano = QTextEdit(); self.plano.setReadOnly(True)
        btn = QPushButton("Gerar plano a partir da última análise")
        btn.clicked.connect(lambda: self.iniciar("plano_de_acao", [], self.mostrar_plano))
        layout.addWidget(btn); layout.addWidget(self.plano)
        return aba

    def _aba_estudio(self):
        aba = QWidget(); layout = QVBoxLayout(aba)
        layout.addWidget(QLabel("Crie uma carta, resumo direcionado e checklist usando uma vaga salva. Revise todo o conteúdo antes de candidatar."))
        linha = QHBoxLayout()
        self.seletor_vaga = QComboBox()
        self.btn_gerar_pacote = QPushButton("Gerar material")
        self.btn_gerar_pacote.clicked.connect(self.gerar_pacote)
        self.btn_exportar_pacote = QPushButton("Exportar DOCX")
        self.btn_exportar_pacote.setEnabled(False)
        self.btn_exportar_pacote.clicked.connect(self.exportar_pacote)
        linha.addWidget(self.seletor_vaga, 1); linha.addWidget(self.btn_gerar_pacote); linha.addWidget(self.btn_exportar_pacote)
        self.pacote_texto = QTextEdit(); self.pacote_texto.setReadOnly(True)
        layout.addLayout(linha); layout.addWidget(self.pacote_texto)
        return aba

    def iniciar(self, operacao, args, callback):
        if self.thread:
            return
        if operacao == "conversar" and not args[0].strip():
            return
        self.thread = QThread(self); self.worker = CareerWorker(operacao, *args)
        self.worker.moveToThread(self.thread); self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(callback); self.worker.failed.connect(self.erro)
        self.worker.finished.connect(self.thread.quit); self.worker.failed.connect(self.thread.quit)
        self.thread.finished.connect(self.finalizar); self.thread.finished.connect(self.worker.deleteLater); self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

    def finalizar(self):
        self.thread = self.worker = None

    def erro(self, mensagem):
        QMessageBox.critical(self, "Central de Carreira", mensagem)

    def salvar_oportunidade(self):
        titulo = self.o_titulo.text().strip()
        if not titulo:
            QMessageBox.warning(self, "Oportunidade", "Informe o título da vaga."); return
        try:
            pipeline = self._dados_pipeline()
        except ValueError as error:
            QMessageBox.warning(self, "Oportunidade", str(error))
            return
        oportunidade_id = self.db.salvar_oportunidade(titulo, self.o_empresa.text().strip(), self.o_plataforma.currentText(), self.o_url.text().strip(), self.o_descricao.toPlainText().strip(), self.o_status.currentText())
        self.db.atualizar_candidatura(oportunidade_id, **pipeline)
        self.o_titulo.clear(); self.o_empresa.clear(); self.o_url.clear(); self.o_descricao.clear(); self.carregar_oportunidades()
        self.status_busca.setText(f"Oportunidade #{oportunidade_id} salva. Se ela já existia, os dados foram atualizados sem criar duplicidade.")

    def atualizar_etapa_oportunidade(self):
        linha = self.tabela.currentRow()
        if linha < 0:
            QMessageBox.information(self, "Oportunidades", "Selecione uma oportunidade para atualizar a etapa.")
            return
        item = self.tabela.item(linha, 0)
        oportunidade_id = item.data(Qt.UserRole)
        try:
            pipeline = self._dados_pipeline()
        except ValueError as error:
            QMessageBox.warning(self, "Oportunidades", str(error))
            return
        self.db.atualizar_candidatura(oportunidade_id, **pipeline)
        self.carregar_oportunidades()
        self.status_busca.setText("Etapa da oportunidade atualizada.")

    def _dados_pipeline(self):
        for label, value in (
            ("Prazo", self.o_prazo.text().strip()),
            ("Data da candidatura", self.o_data_candidatura.text().strip()),
        ):
            if value:
                try:
                    datetime.strptime(value, "%Y-%m-%d")
                except ValueError as error:
                    raise ValueError(f"{label} deve usar o formato AAAA-MM-DD.") from error
        email = self.o_email.text().strip()
        if email and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
            raise ValueError("Informe um e-mail válido para o recrutador.")
        url = self.o_url.text().strip()
        if url and QUrl(url).scheme().casefold() not in {"http", "https"}:
            raise ValueError("O link da vaga deve começar com http:// ou https://.")
        return {
            "status": self.o_status.currentText(),
            "applied_at": self.o_data_candidatura.text().strip(),
            "salary_range": self.o_salario.text().strip(),
            "work_model": self.o_modelo.currentText(),
            "employment_type": self.o_contrato.currentText(),
            "recruiter_name": self.o_recrutador.text().strip(),
            "recruiter_email": email,
            "recruiter_phone": self.o_telefone.text().strip(),
            "next_action": self.o_proxima_acao.text().strip(),
            "next_action_at": self.o_prazo.text().strip(),
            "notes": self.o_descricao.toPlainText().strip(),
        }

    def abrir_oportunidade_selecionada(self, linha, _coluna):
        oportunidade_id = self.tabela.item(linha, 0).data(Qt.UserRole)
        oportunidade = self.db.obter_oportunidade(oportunidade_id)
        if oportunidade and oportunidade["url"]:
            target = QUrl(oportunidade["url"])
            if target.scheme().casefold() not in {"http", "https"}:
                QMessageBox.warning(
                    self, "Abrir oportunidade", "O link informado não é HTTP/HTTPS válido."
                )
                return
            QDesktopServices.openUrl(target)

    def carregar_oportunidades(self):
        dados = self.db.listar_oportunidades(); self.tabela.setRowCount(len(dados))
        for linha, item in enumerate(dados):
            primeira = QTableWidgetItem(item["titulo"] or "-")
            primeira.setData(Qt.UserRole, item["id"])
            self.tabela.setItem(linha, 0, primeira)
            for coluna, chave in enumerate(("empresa", "plataforma", "status", "next_action"), start=1):
                self.tabela.setItem(linha, coluna, QTableWidgetItem(item[chave] or "-"))
            data = str(item["updated_at"] or item["created_at"] or "")[:16]
            self.tabela.setItem(linha, 5, QTableWidgetItem(data or "-"))
        metricas = self.db.metricas_candidaturas()
        self.pipeline_resumo.setText(
            f"<b>{metricas['total']}</b> candidaturas &nbsp; • &nbsp; "
            f"<b>{metricas['retorno']}%</b> de retorno &nbsp; • &nbsp; "
            f"<b>{metricas['entrevistas']}%</b> chegaram a entrevista &nbsp; • &nbsp; "
            f"<b>{metricas['acompanhamentos']}</b> ações pendentes &nbsp; • &nbsp; "
            f"Melhor fonte: <b>{metricas['melhor_fonte']}</b>"
        )
        if hasattr(self, "seletor_vaga"):
            self.seletor_vaga.clear()
            for item in dados:
                label = f"{item['titulo']} — {item['empresa'] or 'Empresa não informada'}"
                self.seletor_vaga.addItem(label, item["id"])

    def carregar_historico_selecionado(self):
        linha = self.tabela.currentRow()
        if linha < 0:
            self.historico_candidatura.setRowCount(0)
            return
        opportunity_id = self.tabela.item(linha, 0).data(Qt.UserRole)
        opportunity = self.db.obter_oportunidade(opportunity_id)
        if opportunity:
            self.o_titulo.setText(opportunity["titulo"] or "")
            self.o_empresa.setText(opportunity["empresa"] or "")
            self.o_url.setText(opportunity["url"] or "")
            self.o_descricao.setPlainText(opportunity["notes"] or opportunity["descricao"] or "")
            for combo, value in (
                (self.o_plataforma, opportunity["plataforma"]),
                (self.o_status, opportunity["status"]),
                (self.o_modelo, opportunity["work_model"]),
                (self.o_contrato, opportunity["employment_type"]),
            ):
                index = combo.findText(value or "")
                if index >= 0:
                    combo.setCurrentIndex(index)
            self.o_salario.setText(opportunity["salary_range"] or "")
            self.o_recrutador.setText(opportunity["recruiter_name"] or "")
            self.o_email.setText(opportunity["recruiter_email"] or "")
            self.o_telefone.setText(opportunity["recruiter_phone"] or "")
            self.o_proxima_acao.setText(opportunity["next_action"] or "")
            self.o_prazo.setText(opportunity["next_action_at"] or "")
            self.o_data_candidatura.setText(opportunity["applied_at"] or "")
        history = self.db.listar_historico_candidatura(opportunity_id)
        self.historico_candidatura.setRowCount(len(history))
        for row, item in enumerate(history):
            change = item["status_to"]
            if item["status_from"]:
                change = f"{item['status_from']} → {item['status_to']}"
            self.historico_candidatura.setItem(row, 0, QTableWidgetItem(str(item["created_at"])[:16]))
            self.historico_candidatura.setItem(row, 1, QTableWidgetItem(change))
            self.historico_candidatura.setItem(row, 2, QTableWidgetItem(item["notes"] or "-"))

    def resposta_chat(self, resposta):
        pergunta = self.chat_input.text().strip()
        self.chat.append(f"<b>Você:</b> {escape(pergunta)}")
        safe_response = escape(str(resposta)).replace("\n", "<br>")
        self.chat.append(f"<b>Assistente:</b> {safe_response}<br>")
        self.chat_input.clear()

    def mostrar_pergunta(self, pergunta):
        self.pergunta_atual = pergunta; self.lbl_pergunta.setText(pergunta); self.resposta.clear(); self.feedback.setText("")

    def avaliar_resposta(self):
        if not self.pergunta_atual:
            QMessageBox.information(self, "Simulador", "Gere uma pergunta antes de avaliar a resposta."); return
        self.iniciar("avaliar_resposta", [self.pergunta_atual, self.resposta.toPlainText(), self.tema.currentText()], self.mostrar_feedback)

    def mostrar_feedback(self, resultado):
        self.feedback.setText(f"Nota: {resultado['nota']}/100\n\n{resultado['feedback']}")

    def mostrar_plano(self, itens):
        self.plano.setPlainText("\n".join(f"• {item}" for item in itens))

    def gerar_pacote(self):
        oportunidade_id = self.seletor_vaga.currentData()
        if oportunidade_id is None:
            QMessageBox.information(self, "Estúdio de candidatura", "Salve uma oportunidade antes de gerar o material.")
            return
        self.iniciar("gerar_pacote", [oportunidade_id], self.mostrar_pacote)

    def mostrar_pacote(self, pacote):
        self.pacote_atual = pacote
        texto = [f"VAGA: {pacote['vaga']}"]
        if pacote["empresa"]:
            texto.append(f"EMPRESA: {pacote['empresa']}")
        texto.extend(["\nCARTA DE APRESENTAÇÃO", pacote["carta"], "\nRESUMO DIRECIONADO", pacote["resumo_direcionado"], "\nPALAVRAS-CHAVE", "\n".join(f"• {x}" for x in pacote["palavras_chave"]), "\nCHECKLIST", "\n".join(f"• {x}" for x in pacote["checklist"])])
        self.pacote_texto.setPlainText("\n".join(texto))
        self.btn_exportar_pacote.setEnabled(True)

    def exportar_pacote(self):
        try:
            destino = self.relatorios.exportar_pacote_candidatura_docx(self.pacote_atual)
            QMessageBox.information(self, "Material criado", f"DOCX salvo em:\n{destino.resolve()}")
        except Exception as erro:
            QMessageBox.critical(self, "Erro ao exportar", str(erro))

    def shutdown(self):
        """Interrompe a operação da Central de Carreira durante a saída."""
        shutdown_threads((self.thread,))

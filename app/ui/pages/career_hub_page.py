from urllib.parse import quote_plus

from PySide6.QtCore import QThread, QUrl, Signal, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit,
    QLineEdit, QComboBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QTabWidget, QMessageBox,
)

from app.database.sqlite_db import Database
from app.services.career_assistant_service import CareerAssistantService
from app.services.job_search_service import JobSearchService
from app.services.report_service import ReportService
from app.ui.workers import CareerWorker


class CareerHubPage(QWidget):
    """Central V2: oportunidades salvas, mentor de carreira e treino de entrevista."""

    busca_integrada_solicitada = Signal()

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
        titulo.setStyleSheet("font-size:28px;font-weight:bold;color:#1976D2;")
        layout.addWidget(titulo)
        self.perfil_resumo = QLabel()
        self.perfil_resumo.setWordWrap(True)
        self.perfil_resumo.setTextFormat(Qt.RichText)
        self.perfil_resumo.setStyleSheet(
            "background:#EAF3FF;border:1px solid #C9DDF7;border-radius:10px;"
            "padding:14px;color:#174EA6;font-size:13px;"
        )
        layout.addWidget(self.perfil_resumo)
        abas = QTabWidget()
        abas.addTab(self._aba_oportunidades(), "Oportunidades")
        abas.addTab(self._aba_chat(), "Assistente")
        abas.addTab(self._aba_entrevista(), "Simulador")
        abas.addTab(self._aba_plano(), "Plano de ação")
        abas.addTab(self._aba_estudio(), "Estúdio V3")
        layout.addWidget(abas)
        self.carregar_oportunidades()
        self.atualizar_perfil()

    def _aba_oportunidades(self):
        aba = QWidget(); layout = QVBoxLayout(aba)
        instrucao = QLabel(
            "Use a busca integrada para vagas públicas. Nas plataformas que exigem conta, "
            "a pesquisa é aberta no seu navegador para que você entre com seu próprio login."
        )
        instrucao.setWordWrap(True)
        instrucao.setStyleSheet("color:#52606D;padding:4px 0;")
        layout.addWidget(instrucao)
        acoes_busca = QHBoxLayout()
        self.btn_busca_integrada = QPushButton("Buscar vagas para meu currículo")
        self.btn_busca_integrada.clicked.connect(self.busca_integrada_solicitada.emit)
        acoes_busca.addWidget(self.btn_busca_integrada)
        for plataforma in ("LinkedIn", "Gupy", "Indeed", "Catho", "Vagas.com"):
            botao = QPushButton(f"Abrir {plataforma}")
            botao.clicked.connect(lambda _=False, nome=plataforma: self.abrir_plataforma(nome))
            acoes_busca.addWidget(botao)
        acoes_busca.addStretch()
        layout.addLayout(acoes_busca)
        self.status_busca = QLabel("")
        self.status_busca.setWordWrap(True)
        self.status_busca.setStyleSheet("color:#52606D;")
        layout.addWidget(self.status_busca)
        linha = QHBoxLayout()
        self.o_titulo = QLineEdit(); self.o_titulo.setPlaceholderText("Título da vaga *")
        self.o_empresa = QLineEdit(); self.o_empresa.setPlaceholderText("Empresa")
        self.o_plataforma = QComboBox(); self.o_plataforma.addItems(["Manual", "LinkedIn", "Gupy", "Indeed", "Catho"])
        linha.addWidget(self.o_titulo, 2); linha.addWidget(self.o_empresa, 2); linha.addWidget(self.o_plataforma, 1)
        layout.addLayout(linha)
        self.o_url = QLineEdit(); self.o_url.setPlaceholderText("Link da vaga (opcional)")
        self.o_descricao = QTextEdit(); self.o_descricao.setPlaceholderText("Descrição ou observações da vaga (opcional)"); self.o_descricao.setMaximumHeight(100)
        self.o_status = QComboBox(); self.o_status.addItems(["Salva", "Candidatura enviada", "Entrevista", "Encerrada"])
        self.o_salvar = QPushButton("Salvar oportunidade")
        self.o_salvar.clicked.connect(self.salvar_oportunidade)
        self.o_atualizar_status = QPushButton("Atualizar etapa da selecionada")
        self.o_atualizar_status.clicked.connect(self.atualizar_etapa_oportunidade)
        acoes_oportunidade = QHBoxLayout(); acoes_oportunidade.addWidget(self.o_salvar); acoes_oportunidade.addWidget(self.o_atualizar_status); acoes_oportunidade.addStretch()
        layout.addWidget(self.o_url); layout.addWidget(self.o_descricao); layout.addWidget(self.o_status); layout.addLayout(acoes_oportunidade)
        self.tabela = QTableWidget(0, 5); self.tabela.setHorizontalHeaderLabels(["Vaga", "Empresa", "Plataforma", "Status", "Atualizada"])
        self.tabela.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tabela.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabela.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabela.cellDoubleClicked.connect(self.abrir_oportunidade_selecionada)
        layout.addWidget(self.tabela); self.carregar_oportunidades()
        return aba

    def atualizar_perfil(self):
        """Exibe uma síntese determinística da última análise, sem nova chamada à IA."""
        analise = self.db.obter_ultima_analise()
        if not analise:
            self.perfil_resumo.setText(
                "<b>Seu perfil ainda não está ativo.</b> Importe e analise um currículo em “Meu currículo” "
                "para receber diagnóstico, títulos recomendados e buscas personalizadas."
            )
            if hasattr(self, "btn_busca_integrada"):
                self.btn_busca_integrada.setEnabled(False)
            return
        recomendacao = JobSearchService().recomendacao_para_curriculo()
        habilidades = [x.strip() for x in (analise["hard_skills"] or "").split(";") if x.strip()]
        faltantes = [x.strip() for x in (analise["competencias_faltantes"] or "").split(";") if x.strip()]
        titulos = " · ".join(recomendacao["titulos"][:4])
        palavras = ", ".join(recomendacao["palavras_chave"][:10])
        self.perfil_resumo.setText(
            f"<b>Perfil ativo:</b> {analise['cargo'] or 'Não identificado'} &nbsp; | &nbsp; "
            f"<b>Área:</b> {analise['area'] or 'Não identificada'} &nbsp; | &nbsp; "
            f"<b>ATS:</b> {analise['ats_score'] or 0}%<br>"
            f"<b>Busca recomendada (Brasil):</b> {recomendacao['principal']}<br>"
            f"<b>Títulos relacionados:</b> {titulos}<br>"
            f"<b>Competências identificadas:</b> {', '.join(habilidades[:8]) or 'Não identificadas'}<br>"
            f"<b>Palavras-chave para vagas:</b> {palavras}<br>"
            f"<b>Para desenvolver:</b> {', '.join(faltantes[:4]) or 'Revise as recomendações da análise'}"
        )
        if hasattr(self, "btn_busca_integrada"):
            self.btn_busca_integrada.setEnabled(True)

    def abrir_plataforma(self, plataforma):
        """Abre uma pesquisa oficial sem tentar acessar áreas privadas do candidato."""
        try:
            consulta = JobSearchService().termo_para_curriculo()
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
        oportunidade_id = self.db.salvar_oportunidade(titulo, self.o_empresa.text().strip(), self.o_plataforma.currentText(), self.o_url.text().strip(), self.o_descricao.toPlainText().strip(), self.o_status.currentText())
        self.o_titulo.clear(); self.o_empresa.clear(); self.o_url.clear(); self.o_descricao.clear(); self.carregar_oportunidades()
        self.status_busca.setText(f"Oportunidade #{oportunidade_id} salva. Se ela já existia, os dados foram atualizados sem criar duplicidade.")

    def atualizar_etapa_oportunidade(self):
        linha = self.tabela.currentRow()
        if linha < 0:
            QMessageBox.information(self, "Oportunidades", "Selecione uma oportunidade para atualizar a etapa.")
            return
        item = self.tabela.item(linha, 0)
        oportunidade_id = item.data(Qt.UserRole)
        self.db.atualizar_status_oportunidade(oportunidade_id, self.o_status.currentText())
        self.carregar_oportunidades()
        self.status_busca.setText("Etapa da oportunidade atualizada.")

    def abrir_oportunidade_selecionada(self, linha, _coluna):
        oportunidade_id = self.tabela.item(linha, 0).data(Qt.UserRole)
        oportunidade = self.db.obter_oportunidade(oportunidade_id)
        if oportunidade and oportunidade["url"]:
            QDesktopServices.openUrl(QUrl(oportunidade["url"]))

    def carregar_oportunidades(self):
        dados = self.db.listar_oportunidades(); self.tabela.setRowCount(len(dados))
        for linha, item in enumerate(dados):
            primeira = QTableWidgetItem(item["titulo"] or "-")
            primeira.setData(Qt.UserRole, item["id"])
            self.tabela.setItem(linha, 0, primeira)
            for coluna, chave in enumerate(("empresa", "plataforma", "status"), start=1):
                self.tabela.setItem(linha, coluna, QTableWidgetItem(item[chave] or "-"))
            data = str(item["updated_at"] or item["created_at"] or "")[:16]
            self.tabela.setItem(linha, 4, QTableWidgetItem(data or "-"))
        if hasattr(self, "seletor_vaga"):
            self.seletor_vaga.clear()
            for item in dados:
                label = f"{item['titulo']} — {item['empresa'] or 'Empresa não informada'}"
                self.seletor_vaga.addItem(label, item["id"])

    def resposta_chat(self, resposta):
        pergunta = self.chat_input.text().strip()
        self.chat.append(f"<b>Você:</b> {pergunta}")
        self.chat.append(f"<b>Assistente:</b> {resposta}<br>")
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

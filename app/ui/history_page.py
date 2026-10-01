from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.history_service import HistoryService


class HistoryPage(QWidget):

    def __init__(self):
        super().__init__()

        self.service = HistoryService()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        titulo = QLabel("Histórico de Currículos")
        titulo.setObjectName("pageTitle")

        layout.addWidget(titulo)

        barra = QHBoxLayout()

        self.btn_atualizar = QPushButton("🔄 Atualizar")
        self.btn_abrir = QPushButton("📄 Abrir")
        self.btn_ativar = QPushButton("✓ Usar como ativo")
        self.btn_excluir = QPushButton("🗑 Excluir")
        for botao in (self.btn_atualizar, self.btn_abrir, self.btn_ativar):
            botao.setProperty("secondary", True)
        self.btn_excluir.setProperty("danger", True)

        barra.addWidget(self.btn_atualizar)
        barra.addWidget(self.btn_abrir)
        barra.addWidget(self.btn_ativar)
        barra.addWidget(self.btn_excluir)
        barra.addStretch()

        layout.addLayout(barra)

        self.tabela = QTableWidget()

        self.tabela.setColumnCount(3)
        self.tabela.setHorizontalHeaderLabels(
            ["ID", "Arquivo", "Data"]
        )

        self.tabela.setSelectionBehavior(
            QAbstractItemView.SelectRows
        )

        self.tabela.setEditTriggers(
            QAbstractItemView.NoEditTriggers
        )

        self.tabela.horizontalHeader().setSectionResizeMode(
            1,
            QHeaderView.Stretch
        )

        self.tabela.setColumnWidth(0,60)
        self.tabela.setColumnWidth(2,180)

        layout.addWidget(self.tabela)

        self.btn_atualizar.clicked.connect(self.carregar_curriculos)
        self.btn_abrir.clicked.connect(self.abrir_curriculo)
        self.btn_ativar.clicked.connect(self.definir_curriculo_ativo)
        self.btn_excluir.clicked.connect(self.excluir_curriculo)

        self.carregar_curriculos()

    def carregar_curriculos(self):

        dados = self.service.listar_curriculos()

        self.tabela.setRowCount(len(dados))

        for linha, registro in enumerate(dados):

            self.tabela.setItem(
                linha,0,
                QTableWidgetItem(str(registro[0]))
            )

            self.tabela.setItem(
                linha,1,
                QTableWidgetItem(registro[1])
            )

            self.tabela.setItem(
                linha,2,
                QTableWidgetItem(str(registro[2]))
            )

    def abrir_curriculo(self):

        linha = self.tabela.currentRow()

        if linha == -1:
            QMessageBox.information(
                self,
                "Aviso",
                "Selecione um currículo."
            )
            return

        resume_id = int(self.tabela.item(linha,0).text())

        dados = self.service.obter_curriculo(resume_id)

        QMessageBox.information(
            self,
            dados[1],
            dados[3]
        )

    def excluir_curriculo(self):

        linha = self.tabela.currentRow()

        if linha == -1:
            QMessageBox.information(
                self,
                "Aviso",
                "Selecione um currículo."
            )
            return

        resume_id = int(self.tabela.item(linha,0).text())

        resposta = QMessageBox.question(
            self,
            "Excluir currículo e dados derivados",
            "Esta ação removerá a cópia interna do currículo, análises, Job Matches, "
            "candidaturas, conversas, entrevistas, objetivo e confirmações vinculados, além dos materiais gerados. "
            "Histórico legado sem perfil é removido separadamente na Central de Carreira. "
            "O arquivo original não será apagado.\n\n"
            "Deseja continuar?"
        )

        if resposta == QMessageBox.Yes:
            self.service.excluir_curriculo(resume_id)
            self.carregar_curriculos()
            QMessageBox.information(
                self, "Exclusão concluída", "O currículo e seus dados derivados foram removidos."
            )

    def definir_curriculo_ativo(self):
        linha = self.tabela.currentRow()
        if linha == -1:
            QMessageBox.information(self, "Currículo ativo", "Selecione um currículo.")
            return
        resume_id = int(self.tabela.item(linha, 0).text())
        self.service.definir_curriculo_ativo(resume_id)
        QMessageBox.information(self, "Currículo ativo", "Currículo ativo atualizado para buscas e análises futuras.")


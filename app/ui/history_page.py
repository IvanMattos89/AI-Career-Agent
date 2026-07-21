from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QMessageBox,
    QHeaderView,
    QAbstractItemView
)

from app.services.history_service import HistoryService


class HistoryPage(QWidget):

    def __init__(self):
        super().__init__()

        self.service = HistoryService()

        layout = QVBoxLayout(self)

        titulo = QLabel("Histórico de Currículos")
        titulo.setStyleSheet("""
            font-size:18px;
            font-weight:bold;
            padding:10px;
        """)

        layout.addWidget(titulo)

        barra = QHBoxLayout()

        self.btn_atualizar = QPushButton("🔄 Atualizar")
        self.btn_abrir = QPushButton("📄 Abrir")
        self.btn_excluir = QPushButton("🗑 Excluir")

        barra.addWidget(self.btn_atualizar)
        barra.addWidget(self.btn_abrir)
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
            "Excluir",
            "Deseja excluir este currículo?"
        )

        if resposta == QMessageBox.Yes:
            self.service.excluir_curriculo(resume_id)
            self.carregar_curriculos()


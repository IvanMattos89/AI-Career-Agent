from datetime import date

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from app.services.opportunity_tracking import OpportunityTracking


class OpportunityReport(QDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.tracker = OpportunityTracking(db)
        self.setWindowTitle("Oportunidades e confirmações")
        self.resize(1100, 650)
        layout = QVBoxLayout(self)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        note = QLabel("Novas e repetidas: período selecionado. Disponibilidade: última confirmação registrada. "
                      "Ausência na busca não comprova encerramento. O catálogo é compartilhado; o pipeline usa o currículo ativo.")
        note.setWordWrap(True)
        layout.addWidget(note)
        bar = QHBoxLayout()
        self.days = QSpinBox()
        self.days.setRange(1, 365)
        self.days.setValue(7)
        self.kind = QComboBox()
        self.kind.addItems(["Todas", "Novas", "Duplicadas/repetidas", "Encerradas", "Pendentes de confirmação"])
        bar.addWidget(QLabel("Últimos dias"))
        bar.addWidget(self.days)
        bar.addWidget(self.kind)
        layout.addLayout(bar)
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["Vaga", "Empresa", "Multinacional", "Disponibilidade", "Remuneração", "Novas", "Repetições"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.table)
        link_bar = QHBoxLayout()
        link_bar.addWidget(QLabel("Link da vaga"))
        self.link = QLineEdit()
        self.link.setReadOnly(True)
        link_bar.addWidget(self.link, 1)
        self.open_button = QPushButton("Abrir anúncio")
        self.open_button.clicked.connect(self.open_listing)
        link_bar.addWidget(self.open_button)
        layout.addLayout(link_bar)
        self.table.currentCellChanged.connect(self.update_link)
        actions = QHBoxLayout()
        for label, callback in [("Registrar evidência da empresa", self.company), ("Confirmar disponibilidade", self.availability),
                                ("Exportar relatório CSV", self.export), ("Atualizar", self.reload)]:
            button = QPushButton(label)
            button.clicked.connect(callback)
            actions.addWidget(button)
        layout.addLayout(actions)
        self.kind.currentIndexChanged.connect(self.reload)
        self.days.valueChanged.connect(self.reload)
        self.reload()

    def reload(self):
        rows = self.tracker.report(self.days.value())
        counts = {"novas": sum(bool(r["new_count"]) for r in rows), "repetidas": sum(bool(r["duplicates"]) for r in rows),
                  "encerradas": sum(r["availability"] == "encerrada" for r in rows),
                  "pendentes": sum(r["availability"] == "pendente" for r in rows)}
        pipeline = self.tracker.pipeline(self.db.obter_curriculo_ativo_id())
        self.summary.setText(f"Catálogo: {len(rows)} vagas • Novas: {counts['novas']} • Repetidas: {counts['repetidas']} • "
                             f"Encerradas: {counts['encerradas']} • Pendentes: {counts['pendentes']}\n"
                             f"Currículo ativo — oportunidades: {pipeline['oportunidades']} • candidaturas: {pipeline['candidaturas']} • entrevistas em curso: {pipeline['entrevistas']}")
        index = self.kind.currentIndex()
        self.rows = [r for r in rows if index == 0 or (index == 1 and r["new_count"]) or
                     (index == 2 and r["duplicates"]) or (index == 3 and r["availability"] == "encerrada") or
                     (index == 4 and r["availability"] == "pendente")]
        self.table.setCurrentCell(-1, -1)
        self.table.setRowCount(len(self.rows))
        for i, row in enumerate(self.rows):
            values = [row["title"], row["company"], row["company_evidence"]["label"], row["availability"],
                      row["salary"] or "Não informada", row["new_count"], row["duplicates"]]
            for j, value in enumerate(values):
                cell = QTableWidgetItem(str(value))
                cell.setToolTip(f"Anúncio: {row['url']}\nEmpresa: {row['company_evidence'].get('source', '')}\n"
                                f"Disponibilidade: {row['availability_source'] or ''} — {row['checked_on'] or ''}")
                self.table.setItem(i, j, cell)

        self.update_link()

    def update_link(self):
        index = self.table.currentRow()
        selected = 0 <= index < len(self.rows)
        url = (self.rows[index]["url"] or "").strip() if selected else ""
        self.link.setText(url)
        self.link.setCursorPosition(0)
        self.link.setPlaceholderText("Link não informado" if selected else "Selecione uma vaga")
        target = QUrl(url)
        self.open_button.setEnabled(bool(target.isValid() and target.host() and target.scheme() in {"http", "https"}))

    def open_listing(self):
        if self.open_button.isEnabled() and not QDesktopServices.openUrl(QUrl(self.link.text())):
            QMessageBox.warning(self, "Abrir anúncio", "Não foi possível abrir o navegador. Copie o link da vaga.")

    def selected(self):
        index = self.table.currentRow()
        if index < 0:
            QMessageBox.information(self, "Seleção", "Selecione uma vaga.")
            return None
        return self.rows[index]

    def evidence_dialog(self, title, choices, source=""):
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        form = QFormLayout(dialog)
        status = QComboBox()
        for label, code in choices:
            status.addItem(label, code)
        origin = QLineEdit(source)
        checked = QLineEdit(date.today().isoformat())
        note = QLineEdit()
        note.setPlaceholderText("Trecho ou fato que sustenta a confirmação")
        form.addRow("Classificação", status)
        form.addRow("Fonte (URL ou referência)", origin)
        form.addRow("Data (AAAA-MM-DD)", checked)
        form.addRow("Evidência", note)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        if dialog.exec() == QDialog.Accepted:
            return status.currentData(), origin.text().strip(), checked.text().strip(), note.text().strip()
        return None

    def company(self):
        row = self.selected()
        if row is None:
            return
        result = self.evidence_dialog("Evidência sobre a empresa", [("A confirmar", "pendente"), ("Multinacional confirmada", "confirmada"), ("Não multinacional", "nao")])
        if result:
            try:
                self.tracker.set_company(row["company"], *result)
                self.reload()
            except ValueError as error:
                QMessageBox.warning(self, "Verifique os dados", str(error))

    def availability(self):
        row = self.selected()
        if row is None:
            return
        result = self.evidence_dialog("Disponibilidade da vaga", [("Pendente de confirmação", "pendente"), ("Aberta", "aberta"), ("Encerrada", "encerrada")], row["url"])
        if result:
            try:
                self.tracker.set_availability(row["id"], *result)
                self.reload()
            except ValueError as error:
                QMessageBox.warning(self, "Verifique os dados", str(error))

    def export(self):
        path, _ = QFileDialog.getSaveFileName(self, "Exportar relatório", "oportunidades.csv", "CSV (*.csv)")
        if path:
            try:
                self.tracker.export(path, self.rows)
            except OSError as error:
                QMessageBox.warning(self, "Falha na exportação", str(error))

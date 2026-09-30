"""Pré-visualização editável e auditável do currículo direcionado."""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class ResumePreviewDialog(QDialog):
    """Permite revisar conteúdo e evidências antes de criar o arquivo final."""

    def __init__(self, data, report_service, parent=None):
        super().__init__(parent)
        self.data = data
        self.report_service = report_service
        self.setWindowTitle("Revisar currículo direcionado")
        self.resize(1050, 760)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        title = QLabel("Currículo direcionado à vaga")
        title.setObjectName("dialogTitle")
        subtitle = QLabel(
            "Revise o texto antes de exportar. Requisitos sem evidência não são adicionados automaticamente."
        )
        subtitle.setObjectName("mutedText")
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        score = data.get("score_ats", {})
        if score:
            score_label = QLabel(
                f"Completude documental: original {score.get('antes', 0)}%  →  "
                f"direcionado {score.get('depois', 0)}%   |   {score.get('criterios', '')}"
            )
            score_label.setObjectName("profileBanner")
            score_label.setWordWrap(True)
            layout.addWidget(score_label)
        if data.get("alertas"):
            alerts = QLabel("  ".join(f"Atenção: {item}" for item in data["alertas"]))
            alerts.setObjectName("warningBanner")
            alerts.setWordWrap(True)
            layout.addWidget(alerts)

        tabs = QTabWidget()
        preview_tab = QWidget()
        preview_layout = QVBoxLayout(preview_tab)
        preview_layout.setContentsMargins(8, 10, 8, 8)
        self.editor = QTextEdit()
        self.editor.setPlainText(data["texto_previa"])
        self.editor.setPlaceholderText("Conteúdo do currículo direcionado")
        preview_layout.addWidget(self.editor)
        tabs.addTab(preview_tab, "Prévia editável")

        evidence_tab = QWidget()
        evidence_layout = QVBoxLayout(evidence_tab)
        evidence_layout.setContentsMargins(8, 10, 8, 8)
        self.evidence = QTableWidget(0, 6)
        self.evidence.setHorizontalHeaderLabels(
            ["Requisito", "Prioridade", "Status", "Evidência", "Fonte", "Ação"]
        )
        self.evidence.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.evidence.setAlternatingRowColors(True)
        self.evidence.setWordWrap(True)
        self._load_evidence()
        evidence_layout.addWidget(self.evidence)
        tabs.addTab(evidence_tab, "Matriz de evidências")
        layout.addWidget(tabs, 1)

        actions = QHBoxLayout()
        actions.addStretch()
        close_button = QPushButton("Fechar")
        close_button.setProperty("secondary", True)
        docx_button = QPushButton("Salvar em Word")
        pdf_button = QPushButton("Salvar em PDF")
        close_button.clicked.connect(self.reject)
        docx_button.clicked.connect(self.save_docx)
        pdf_button.clicked.connect(self.save_pdf)
        actions.addWidget(close_button)
        actions.addWidget(docx_button)
        actions.addWidget(pdf_button)
        layout.addLayout(actions)

    def _load_evidence(self):
        matrix = self.data.get("matriz_evidencias", [])
        self.evidence.setRowCount(len(matrix))
        keys = ("requisito", "prioridade", "status", "evidencia", "fonte", "acao")
        for row, evidence in enumerate(matrix):
            for column, key in enumerate(keys):
                item = QTableWidgetItem(str(evidence.get(key, "")))
                if key == "status":
                    item.setData(Qt.UserRole, evidence.get("status"))
                self.evidence.setItem(row, column, item)
        header = self.evidence.horizontalHeader()
        header.setStretchLastSection(True)
        self.evidence.resizeColumnsToContents()
        self.evidence.setColumnWidth(3, max(260, self.evidence.columnWidth(3)))

    def _export_data(self):
        data = dict(self.data)
        data["texto_editado"] = self.editor.toPlainText().strip()
        if not data["texto_editado"]:
            raise ValueError("O currículo não pode ser exportado sem conteúdo.")
        return data

    def save_docx(self):
        destination, _ = QFileDialog.getSaveFileName(
            self, "Salvar currículo direcionado", "curriculo_direcionado.docx",
            "Word (*.docx)",
        )
        if not destination:
            return
        try:
            destination = self.report_service.exportar_curriculo_adaptado_docx(
                self._export_data(), destination,
            )
            QMessageBox.information(self, "Currículo salvo", f"Word salvo em:\n{Path(destination).resolve()}")
        except (OSError, ValueError) as error:
            QMessageBox.critical(self, "Não foi possível salvar", str(error))

    def save_pdf(self):
        destination, _ = QFileDialog.getSaveFileName(
            self, "Salvar currículo direcionado", "curriculo_direcionado.pdf", "PDF (*.pdf)"
        )
        if not destination:
            return
        try:
            self.report_service.exportar_curriculo_adaptado_pdf(self._export_data(), destination)
            QMessageBox.information(self, "Currículo salvo", f"PDF salvo em:\n{destination}")
        except (OSError, ValueError) as error:
            QMessageBox.critical(self, "Não foi possível salvar", str(error))

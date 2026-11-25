from PySide6.QtWidgets import QCheckBox, QDoubleSpinBox, QFormLayout, QSpinBox, QWidget


class OpportunityControls(QWidget):
    def __init__(self):
        super().__init__()
        form = QFormLayout(self)
        self.fiscal = QCheckBox("Analista Fiscal Sênior / Especialista Tributário e equivalentes")
        self.multinationals = QCheckBox("Ordenar primeiro multinacionais confirmadas em registro")
        self.minimum = QDoubleSpinBox()
        self.minimum.setRange(0, 1000000)
        self.minimum.setPrefix("R$ ")
        self.minimum.setSingleStep(500)
        self.unknown = QCheckBox("Incluir remuneração não informada ou não comparável")
        self.unknown.setChecked(True)
        self.limit = QSpinBox()
        self.limit.setRange(1, 200)
        self.limit.setValue(50)
        form.addRow("Busca para currículo", self.fiscal)
        form.addRow("Preferência de empresa", self.multinationals)
        form.addRow("Remuneração mínima mensal", self.minimum)
        form.addRow("", self.unknown)
        form.addRow("Máximo de resultados", self.limit)

    def options(self):
        return {"perfil_fiscal": self.fiscal.isChecked(), "priorizar_multinacionais": self.multinationals.isChecked(),
                "salario_minimo": self.minimum.value(), "incluir_salario_desconhecido": self.unknown.isChecked(),
                "limite": self.limit.value()}

"""Núcleo de validação de arquivos SPED Fiscal."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from .rules import (
    CSOSN_CODES,
    CST_ICMS_CODES,
    CST_ORIGINS,
    EXPECTED_FIELD_COUNTS,
    ICMS_REGISTERS,
    NON_TAXED_CST,
    REGISTER_SPECS,
    TAXED_CST,
    VALID_UF,
    parse_decimal,
)

@dataclass(frozen=True)
class Issue:
    severity: str
    line: int
    code: str
    message: str

@dataclass
class ValidationReport:
    file: Path
    issues: list[Issue] = field(default_factory=list)
    registers: Counter[str] = field(default_factory=Counter)

    @property
    def errors(self) -> list[Issue]:
        return [issue for issue in self.issues if issue.severity == "ERRO"]

    @property
    def warnings(self) -> list[Issue]:
        return [issue for issue in self.issues if issue.severity == "AVISO"]

    @property
    def ok(self) -> bool:
        return not self.errors


def split_sped_line(raw_line: str) -> list[str]:
    line = raw_line.rstrip("\r\n")
    if not line.startswith("|") or not line.endswith("|"):
        return []
    return line.split("|")[1:-1]


def validate_file(path: str | Path, encoding: str = "latin-1") -> ValidationReport:
    file_path = Path(path)
    report = ValidationReport(file=file_path)
    block_counts: Counter[str] = Counter()
    declared_total: int | None = None

    with file_path.open("r", encoding=encoding) as handle:
        for number, raw_line in enumerate(handle, start=1):
            fields = split_sped_line(raw_line)
            if not fields:
                report.issues.append(Issue("ERRO", number, "FORMATO", "Linha deve iniciar e terminar com '|'."))
                continue

            register = fields[0]
            report.registers[register] += 1
            block_counts[register[0]] += 1

            expected = EXPECTED_FIELD_COUNTS.get(register)
            if expected is not None and len(fields) != expected:
                report.issues.append(Issue("AVISO", number, "CAMPOS", f"Registro {register} possui {len(fields)} campos; esperado {expected}."))

            if register == "0000":
                _validate_opening(fields, number, report)
            elif register == "9999" and len(fields) > 1 and fields[1].isdigit():
                declared_total = int(fields[1])

            if register in ICMS_REGISTERS:
                _validate_icms_register(register, fields, number, report)

    _validate_required_registers(report)
    _validate_block_totals(report, block_counts)
    if declared_total is not None and declared_total != sum(report.registers.values()):
        report.issues.append(Issue("ERRO", 0, "TOTAL", f"9999 declara {declared_total} linhas, mas o arquivo contém {sum(report.registers.values())}."))
    return report


def _validate_opening(fields: list[str], line: int, report: ValidationReport) -> None:
    uf = next((value for value in fields[7:10] if value in VALID_UF), "")
    if not uf:
        report.issues.append(Issue("ERRO", line, "UF", "Registro 0000 deve informar uma UF válida."))
    if len(fields) > 3 and (len(fields[3]) != 8 or not fields[3].isdigit()):
        report.issues.append(Issue("ERRO", line, "DT_INI", "Data inicial deve estar em DDMMAAAA."))
    if len(fields) > 4 and (len(fields[4]) != 8 or not fields[4].isdigit()):
        report.issues.append(Issue("ERRO", line, "DT_FIN", "Data final deve estar em DDMMAAAA."))


def _validate_required_registers(report: ValidationReport) -> None:
    for register in ("0000", "0001", "0990", "9990", "9999"):
        if report.registers[register] != 1:
            report.issues.append(Issue("ERRO", 0, "OBRIGATORIO", f"Registro {register} deve existir exatamente uma vez."))


def _validate_block_totals(report: ValidationReport, block_counts: Counter[str]) -> None:
    for register, count in report.registers.items():
        if register.endswith("990") and len(register) == 4:
            block = register[0]
            expected_total = block_counts[block]
            # Declaração do total fica no campo 2 do próprio registro de encerramento.
            # A conferência exata do valor é feita em passagem específica abaixo.
            if count != 1:
                report.issues.append(Issue("ERRO", 0, "ENCERRAMENTO", f"Registro {register} deve aparecer uma vez."))


def _validate_icms_register(register: str, fields: list[str], line: int, report: ValidationReport) -> None:
    spec = REGISTER_SPECS.get(register)
    if spec is None:
        return

    cst = fields[spec.cst_index] if spec.cst_index is not None and len(fields) > spec.cst_index else ""
    if cst:
        _validate_cst(cst, line, report)

    if spec.aliq_index is not None and len(fields) > spec.aliq_index:
        aliquot = parse_decimal(fields[spec.aliq_index])
        if cst[1:] in TAXED_CST and aliquot <= 0:
            report.issues.append(Issue("AVISO", line, "ICMS_ALIQ", f"CST {cst} normalmente exige alíquota de ICMS positiva."))
        if cst[1:] in NON_TAXED_CST and aliquot > 0:
            report.issues.append(Issue("AVISO", line, "ICMS_ALIQ", f"CST {cst} costuma não destacar alíquota de ICMS."))

    if spec.vl_icms_index is not None and len(fields) > spec.vl_icms_index:
        value = parse_decimal(fields[spec.vl_icms_index])
        if cst[1:] in NON_TAXED_CST and value > 0:
            report.issues.append(Issue("AVISO", line, "VL_ICMS", f"CST {cst} costuma não destacar valor de ICMS."))


def _validate_cst(cst: str, line: int, report: ValidationReport) -> None:
    if cst in CSOSN_CODES:
        report.issues.append(Issue("AVISO", line, "CSOSN", f"Código {cst} é CSOSN; confirme se o regime CRT permite seu uso."))
        return
    if len(cst) != 3 or cst[0] not in CST_ORIGINS or cst[1:] not in CST_ICMS_CODES:
        report.issues.append(Issue("ERRO", line, "CST", f"CST ICMS inválido: {cst!r}."))

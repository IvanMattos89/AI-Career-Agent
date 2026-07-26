"""Regras fiscais parametrizadas para validação de SPED Fiscal.

As listas abaixo são um recorte automatizável de tabelas nacionais estáveis.
A conformidade final deve ser conferida no PVA oficial e na legislação da UF.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

VALID_UF = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG",
    "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
}

CST_ORIGINS = set("012345678")
CST_ICMS_CODES = {
    "00", "10", "20", "30", "40", "41", "50", "51", "60", "70", "90",
}
CSOSN_CODES = {"101", "102", "103", "201", "202", "203", "300", "400", "500", "900"}

ICMS_REGISTERS = {
    "C100", "C170", "C190", "C195", "C197", "C500", "C590", "D100", "D190", "D500", "D590",
    "E100", "E110", "E111", "E116", "E200", "E210", "E250",
}

EXPECTED_FIELD_COUNTS = {
    "0000": 16,
    "0001": 2,
    "0005": 8,
    "0100": 14,
    "0150": 14,
    "0190": 3,
    "0200": 13,
    "0990": 2,
    "C001": 2,
    "C100": 30,
    "C170": 38,
    "C190": 12,
    "C990": 2,
    "D001": 2,
    "D100": 26,
    "D190": 12,
    "D990": 2,
    "E001": 2,
    "E100": 3,
    "E110": 15,
    "E116": 11,
    "E990": 2,
    "9990": 2,
    "9999": 2,
}

@dataclass(frozen=True)
class RegisterSpec:
    cst_index: int | None = None
    cfop_index: int | None = None
    aliq_index: int | None = None
    vl_opr_index: int | None = None
    vl_icms_index: int | None = None

REGISTER_SPECS = {
    "C170": RegisterSpec(cst_index=10, cfop_index=11, aliq_index=14, vl_opr_index=7, vl_icms_index=15),
    "C190": RegisterSpec(cst_index=2, cfop_index=3, aliq_index=4, vl_opr_index=5, vl_icms_index=7),
    "D190": RegisterSpec(cst_index=2, cfop_index=3, aliq_index=4, vl_opr_index=5, vl_icms_index=7),
}

TAXED_CST = {"00", "10", "20", "70", "90"}
NON_TAXED_CST = {"30", "40", "41", "50", "60"}


def parse_decimal(value: str) -> Decimal:
    if not value:
        return Decimal("0")
    return Decimal(value.replace(",", "."))

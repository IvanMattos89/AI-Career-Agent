"""Interface de linha de comando do validador SPED Fiscal."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict

from .core import validate_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Valida arquivo SPED Fiscal (EFD ICMS/IPI).")
    parser.add_argument("arquivo", help="Caminho do arquivo .txt do SPED Fiscal")
    parser.add_argument("--encoding", default="latin-1", help="Codificação do arquivo (padrão: latin-1)")
    parser.add_argument("--json", action="store_true", help="Emite relatório em JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = validate_file(args.arquivo, encoding=args.encoding)

    if args.json:
        print(json.dumps({
            "arquivo": str(report.file),
            "ok": report.ok,
            "erros": [asdict(issue) for issue in report.errors],
            "avisos": [asdict(issue) for issue in report.warnings],
            "registros": dict(report.registers),
        }, ensure_ascii=False, indent=2))
    else:
        status = "APROVADO" if report.ok else "REPROVADO"
        print(f"{status}: {report.file}")
        for issue in report.issues:
            location = f"linha {issue.line}" if issue.line else "arquivo"
            print(f"[{issue.severity}] {location} {issue.code}: {issue.message}")
        print(f"Registros lidos: {sum(report.registers.values())}")

    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())

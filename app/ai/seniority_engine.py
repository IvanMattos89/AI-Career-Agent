"""Estimativa auditável de senioridade a partir de trajetória e responsabilidades."""

import re
from datetime import date

from app.services.evidence_service import normalize, source_lines
from app.services.resume_structure_service import ResumeStructureService


def assess(texto: str, today=None) -> dict:
    today = today or date.today()
    structure = ResumeStructureService.from_text(texto)
    # Preserve date separators when extracting periods; evidence clauses are separate.
    lines = [(section.get("key", "additional"), item["text"])
             for section in structure.get("sections", []) for item in section.get("items", [])]
    lines += [("header", line) for line in structure.get("header", [])]
    explicit: list[int] = []
    intervals: list[tuple[int, int]] = []
    time_evidence: list[str] = []
    current_month = today.year * 12 + today.month - 1
    period = re.compile(r"(?:(\d{1,2})[/.-])?((?:19|20)\d{2})\s*[-–—]\s*(?:(?:(\d{1,2})[/.-])?((?:19|20)\d{2})|(atual|presente))", re.I)
    for section, line in lines:
        normalized = normalize(line)
        if section in {"education", "courses", "certifications", "objective"} or re.search(r"\b(?:curso|academia|universidade|faculdade)\b", normalized):
            continue
        declared_years = re.findall(r"(?<!\d)(\d{1,2})\s*(?:de\s+)?anos?\s+(?:de\s+)?(?:experiencia|atuacao)\b", normalized)
        if declared_years:
            explicit.extend(map(int, declared_years))
            time_evidence.append(line)
        work_context = section == "experience" or bool(re.search(r"\b(?:empresa|trabalhei|empregador|cargo)\b", normalized))
        if not work_context:
            continue
        for match in period.finditer(line):
            sm, sy, em, ey, ongoing = match.groups()
            if not 1 <= int(sm or 1) <= 12 or not 1 <= int(em or 12) <= 12:
                continue
            start = int(sy) * 12 + int(sm or 1) - 1
            end = current_month if ongoing else int(ey) * 12 + int(em or 12) - 1
            if start <= end <= current_month and end - start <= 60 * 12:
                intervals.append((start, end))
                time_evidence.append(line)
    months: set[int] = set()
    for start, end in intervals:
        months.update(range(start, end + 1))
    years = max([len(months) // 12, *explicit], default=0)
    signals: dict[str, list[str]] = {"autonomia": [], "complexidade": [], "responsabilidade": []}
    patterns = {
        "autonomia": r"\b(?:autonomia|decidi|defini|decisoes tecnicas)\b",
        "complexidade": r"\b(?:problemas? complexos?|causa raiz|reconciliacao complexa|integracao entre|multiplas areas)\b",
        "responsabilidade": r"\b(?:responsavel|liderei|coordenei|conduzi|orientei|implantei)\b",
    }
    for section, line in source_lines(structure):
        normalized = normalize(line)
        if section in {"education", "courses", "certifications", "objective"} or re.search(r"\b(?:curso|academia|sem|nao|nunca)\b", normalized):
            continue
        for key, pattern in patterns.items():
            if re.search(pattern, normalized):
                signals[key].append(line)
    level = "Não identificado"
    if years >= 5 and all(signals.values()):
        level = "Sênior"
    elif years > 0 and signals["autonomia"] and signals["responsabilidade"]:
        level = "Pleno"
    else:
        for section, line in lines:
            if section == "experience" and re.search(r"\bjunior\b", normalize(line)):
                level = "Júnior"
                break
    return {"nivel": level, "anos": years, "evidencias_tempo": list(dict.fromkeys(time_evidence)),
            "sinais": signals,
            "limitacoes": "Estimativa heurística, não certificação de senioridade. Tempo isolado não define nível. "
                          "Períodos sem contexto profissional e títulos de objetivo não entram; meses sobrepostos contam uma vez."}


def experience_years(texto: str) -> int:
    return assess(texto)["anos"]


def estimate(texto: str) -> str:
    return assess(texto)["nivel"]

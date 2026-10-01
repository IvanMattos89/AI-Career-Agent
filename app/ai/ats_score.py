"""Completude documental: cinco dimensões de presença/clareza, sem premiar senioridade."""

import re

from app.services.resume_structure_service import ResumeStructureService


def assess(data: dict) -> dict:
    text = data.get("texto_curriculo", "")
    structure = ResumeStructureService.from_text(text)
    sections: dict[str, list[str]] = {key: [] for key in ("summary", "objective", "experience", "education", "skills", "technologies", "languages")}
    for section in structure.get("sections", []):
        if section["key"] in sections:
            sections[section["key"]].extend(item["text"] for item in section.get("items", []))
    header_lines = structure.get("header", [])
    header = " ".join(header_lines)
    first_line = header_lines[0].split("|")[0].strip() if header_lines else ""
    named = 2 <= len(first_line.split()) <= 8 and not re.search(r"[@\d]", first_line)
    trajectory = " ".join(sections["experience"])
    entry_level = re.search(r"primeira oportunidade|sem experi[eê]ncia profissional|primeiro emprego", text, re.I)
    # Text outside explicit sections is retained by the parser, but not assumed to fill them.
    checks = {
        "identificacao_contato": bool(named and (re.search(r"\b[^\s@]+@[^\s@]+\.[^\s@]+", header) or re.search(r"\d[\d ()+-]{7,}\d", header))),
        "objetivo_resumo": len(" ".join(sections["summary"] + sections["objective"]).split()) >= 5,
        "trajetoria_declarada": len(trajectory.split()) >= 5 or bool(entry_level),
        "formacao": len(" ".join(sections["education"]).split()) >= 3,
        "competencias_declaradas": bool(sections["skills"] or sections["technologies"] or sections["languages"]),
    }
    if not text:
        # Compatibility for a parser called without source: do not invent missing sections.
        checks["objetivo_resumo"] = len(str(data.get("resumo", "")).split()) >= 5
        checks["competencias_declaradas"] = bool(data.get("hard_skills") or data.get("tecnologias") or data.get("idiomas"))
    return {"pontuacao": sum(checks.values()) * 20, "teto": 100, "secoes": checks,
            "limitacao": "Presença e clareza mínima de cinco seções, 20 pontos cada; não mede competência, tempo de experiência ou aderência à vaga. "
                         "Seções não reconhecidas precisam de revisão manual. Primeira oportunidade explicitada preenche trajetória."}


def calculate(data: dict) -> int:
    return assess(data)["pontuacao"]

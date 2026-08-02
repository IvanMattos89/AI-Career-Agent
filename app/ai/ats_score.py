from typing import Dict


def calculate(data: Dict) -> int:
    """Indicador determinístico de qualidade, sem contar a mesma skill duas vezes."""
    score = 0
    if data.get("cargo"):
        score += 12
    if data.get("area"):
        score += 8
    if data.get("senioridade"):
        score += 8

    years = max(0, int(data.get("anos_experiencia") or 0))
    score += 15 if years >= 8 else 12 if years >= 5 else 8 if years >= 2 else 0

    unique_skills = {
        str(item).strip().casefold()
        for field in ("hard_skills", "tecnologias")
        for item in data.get(field, [])
        if str(item).strip()
    }
    score += min(len(unique_skills) * 3, 20)
    score += min(len(data.get("idiomas", [])) * 3, 6)
    score += min(len(data.get("certificacoes", [])) * 3, 6)
    if len(str(data.get("resumo", "")).strip()) >= 80:
        score += 12
    score += min(len(data.get("pontos_fortes", [])), 5)
    score += min(len(data.get("recomendacoes", [])), 5)
    return min(score, 100)

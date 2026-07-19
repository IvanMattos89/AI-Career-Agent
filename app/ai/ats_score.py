from typing import Dict


def calculate(data: Dict) -> int:

    score = 0

    if data.get("cargo"):
        score += 15

    if data.get("area"):
        score += 10

    if data.get("senioridade"):
        score += 10

    score += min(len(data.get("hard_skills", [])) * 3, 15)

    score += min(len(data.get("tecnologias", [])) * 2, 15)

    score += min(len(data.get("idiomas", [])) * 5, 10)

    score += min(len(data.get("certificacoes", [])) * 5, 10)

    resumo = data.get("resumo", "")

    if len(resumo) >= 80:
        score += 15

    return min(score, 100)

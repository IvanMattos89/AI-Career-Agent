from dataclasses import dataclass


@dataclass(frozen=True)
class ScoreClassification:
    code: str
    label: str


def classify_score(score: int) -> ScoreClassification:
    """Classifica uma nota de 0 a 100 sem depender da interface."""
    score = max(0, min(100, int(score)))
    if score >= 80:
        return ScoreClassification("excellent", "Excelente")
    if score >= 60:
        return ScoreClassification("good", "Bom")
    if score >= 40:
        return ScoreClassification("regular", "Regular")
    return ScoreClassification("needs_improvement", "Precisa melhorar")

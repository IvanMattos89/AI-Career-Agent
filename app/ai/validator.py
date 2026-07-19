from app.ai.models import ResumeAnalysis


REQUIRED_FIELDS = [
    "cargo",
    "area",
    "confianca",
    "senioridade",
    "hard_skills",
    "soft_skills",
    "tecnologias",
    "idiomas",
    "certificacoes",
    "resumo"
]


def validate(data: dict):

    for campo in REQUIRED_FIELDS:

        if campo not in data:

            data[campo] = [] if campo.endswith("skills") else ""

    if not isinstance(data["hard_skills"], list):
        data["hard_skills"] = []

    if not isinstance(data["soft_skills"], list):
        data["soft_skills"] = []

    if not isinstance(data["tecnologias"], list):
        data["tecnologias"] = []

    if not isinstance(data["idiomas"], list):
        data["idiomas"] = []

    if not isinstance(data["certificacoes"], list):
        data["certificacoes"] = []

    try:
        data["confianca"] = float(data["confianca"])
    except:
        data["confianca"] = 0.0

    return data

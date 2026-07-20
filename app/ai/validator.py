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
    "anos_experiencia",
    "nivel_curriculo",
    "palavras_chave",
    "pontos_fortes",
    "pontos_melhoria",
    "competencias_faltantes",
    "recomendacoes",
    "resumo"
]


LIST_FIELDS = [
    "hard_skills",
    "soft_skills",
    "tecnologias",
    "idiomas",
    "certificacoes",
    "palavras_chave",
    "pontos_fortes",
    "pontos_melhoria",
    "competencias_faltantes",
    "recomendacoes"
]


def validate(data: dict):

    # Garante que todos os campos existam
    for campo in REQUIRED_FIELDS:

        if campo not in data:

            if campo in LIST_FIELDS:
                data[campo] = []

            elif campo == "confianca":
                data[campo] = 0.0

            elif campo == "anos_experiencia":
                data[campo] = 0

            else:
                data[campo] = ""

    # Garante que os campos de lista sejam realmente listas
    for campo in LIST_FIELDS:

        if not isinstance(data[campo], list):
            data[campo] = []

    # Converte confiança
    try:
        data["confianca"] = float(data["confianca"])
    except Exception:
        data["confianca"] = 0.0

    # Converte anos de experiência
    try:
        data["anos_experiencia"] = int(data["anos_experiencia"])
    except Exception:
        data["anos_experiencia"] = 0

    return data
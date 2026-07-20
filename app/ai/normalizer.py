CARGOS = {
    "Análise Fiscal": "Analista Fiscal",
    "Fiscal": "Analista Fiscal",
    "Financeiro": "Analista Financeiro",
    "TI": "Analista de TI",
}


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
    "recomendacoes",
]


def _normalize_list(values):

    if not isinstance(values, list):
        return []

    resultado = []
    vistos = set()

    for item in values:

        if not isinstance(item, str):
            continue

        texto = " ".join(item.strip().split())

        if not texto:
            continue

        chave = texto.casefold()

        if chave not in vistos:
            vistos.add(chave)
            resultado.append(texto)

    return sorted(resultado)


def normalize(data):

    cargo = data.get("cargo", "").strip()

    if cargo in CARGOS:
        data["cargo"] = CARGOS[cargo]
    else:
        data["cargo"] = cargo

    data["area"] = data.get("area", "").strip()

    data["senioridade"] = data.get("senioridade", "").strip()

    data["nivel_curriculo"] = data.get(
        "nivel_curriculo",
        ""
    ).strip()

    data["resumo"] = data.get("resumo", "").strip()

    for campo in LIST_FIELDS:
        data[campo] = _normalize_list(data.get(campo, []))

    return data
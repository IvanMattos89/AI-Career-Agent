CARGOS = {

    "Análise Fiscal": "Analista Fiscal",

    "Fiscal": "Analista Fiscal",

    "Financeiro": "Analista Financeiro",

    "TI": "Analista de TI"
}


def normalize(data):

    cargo = data.get("cargo", "").strip()

    if cargo in CARGOS:

        data["cargo"] = CARGOS[cargo]

    data["tecnologias"] = sorted(
        list(set(data.get("tecnologias", [])))
    )

    data["hard_skills"] = sorted(
        list(set(data.get("hard_skills", [])))
    )

    return data

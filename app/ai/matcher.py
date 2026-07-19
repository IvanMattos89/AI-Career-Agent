import re


def match_resume(resume: dict, vaga: str):

    vaga = vaga.lower()

    tecnologias = resume.get("tecnologias", [])

    hard = resume.get("hard_skills", [])

    itens = tecnologias + hard

    encontrados = []

    for item in itens:

        if re.search(re.escape(item.lower()), vaga):

            encontrados.append(item)

    total = max(len(itens), 1)

    score = round(len(encontrados) / total * 100)

    return {

        "score": score,

        "encontrados": sorted(set(encontrados))

    }

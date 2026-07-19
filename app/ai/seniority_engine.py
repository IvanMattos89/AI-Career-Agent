import re


def estimate(texto: str):

    texto = texto.lower()

    score = 0

    # Tempo de experiência
    anos = re.findall(r"(\d+)\+?\s*anos", texto)

    if anos:
        anos = max(int(a) for a in anos)

        if anos >= 10:
            score += 40
        elif anos >= 8:
            score += 35
        elif anos >= 5:
            score += 25
        elif anos >= 2:
            score += 15

    # Empresas de grande porte
    grandes = [
        "cpfl",
        "deloitte",
        "ey",
        "kpmg",
        "pwc",
        "ambev",
        "nestle",
        "petrobras",
        "vale",
        "ibm",
        "bosch",
        "siemens"
    ]

    for empresa in grandes:
        if empresa in texto:
            score += 5

    # Tecnologias
    tecnologias = [
        "sap",
        "s/4hana",
        "ecc",
        "mastersaf",
        "ktax",
        "tax one",
        "oracle",
        "totvs"
    ]

    for tecnologia in tecnologias:
        if tecnologia in texto:
            score += 3

    # Responsabilidades
    palavras = [
        "governança",
        "compliance",
        "coordenação",
        "liderança",
        "implantação",
        "revisão tributária",
        "planejamento tributário"
    ]

    for palavra in palavras:
        if palavra in texto:
            score += 4

    if score >= 45:
        return "Sênior"

    if score >= 30:
        return "Pleno"

    return "Júnior"

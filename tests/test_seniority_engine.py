from app.ai.seniority_engine import estimate


def test_dez_anos_classifica_como_senior():
    assert estimate("Profissional com 10 anos de experiência") == "Sênior"


def test_oito_anos_classifica_como_pleno():
    assert estimate("Profissional com 8 anos de experiência") == "Pleno"


def test_sem_indicadores_classifica_como_junior():
    assert estimate("Profissional em início de carreira") == "Júnior"


def test_tecnologias_e_responsabilidades_aumentam_score():
    texto = (
        "Profissional com 8 anos de experiência, liderança, "
        "governança, SAP e Oracle"
    )
    assert estimate(texto) == "Sênior"

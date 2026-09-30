from app.ai.seniority_engine import estimate


def test_dez_anos_classifica_como_senior():
    assert estimate("Profissional com 10 anos de experiência") == "Sênior"


def test_oito_anos_classifica_como_pleno():
    assert estimate("Profissional com 8 anos de experiência") == "Pleno"


def test_sem_indicadores_permanece_indeterminado():
    assert estimate("Profissional em início de carreira") == "Não identificado"


def test_tecnologias_e_responsabilidades_aumentam_score():
    texto = (
        "Profissional com 8 anos de experiência, liderei a equipe, "
        "governança, SAP e Oracle"
    )
    assert estimate(texto) == "Sênior"


def test_idade_e_tempo_de_curso_nao_comprovam_senioridade():
    assert estimate("Tenho 35 anos. Curso de 4 anos em contabilidade. SAP Oracle.") == "Não identificado"


def test_palavras_de_responsabilidade_sem_experiencia_nao_bastam():
    assert estimate("Curso de liderança, governança e implantação SAP") == "Não identificado"

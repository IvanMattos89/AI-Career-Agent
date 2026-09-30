import re
import unicodedata


def experience_years(texto: str) -> int:
    texto = _normalize(texto)
    values = re.findall(
        r"(?<!\d)(\d{1,2})\+?\s*anos?\s+(?:de\s+)?(?:experiencia|atuacao)\s*(?:profissional)?\b",
        texto,
    )
    return max((int(value) for value in values), default=0)


def _normalize(texto):
    return "".join(c for c in unicodedata.normalize("NFKD", texto or "") if not unicodedata.combining(c)).lower()


def estimate(texto: str) -> str:
    """Estimativa conservadora: idade, cursos e nomes de sistemas não dão senioridade."""
    texto = _normalize(texto)
    years = experience_years(texto)
    if not years:
        return "Não identificado"
    responsibility = any(re.search(pattern, texto) for pattern in (
        r"\b(?:liderei|coordenei|conduzi|implantei)\b",
        r"\bresponsavel (?:pela|pelo|por)\b",
        r"\bautonomia (?:tecnica|para)\b",
    ))
    # Tempo é um sinal explícito, não certificação de prontidão para Especialista.
    if years >= 10 or (years >= 8 and responsibility):
        return "Sênior"
    if years >= 5:
        return "Pleno"
    return "Júnior"

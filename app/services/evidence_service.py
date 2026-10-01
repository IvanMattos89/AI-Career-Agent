"""Evidências textuais compartilhadas; menção nunca equivale a experiência."""

import html
import re

from app.ai.skill_detector import SkillDetector
from app.services.resume_structure_service import ResumeStructureService

MARKET_TERMS = (
    "SAP S/4HANA", "SAP ECC", "Tax One", "Synchro", "Mastersaf",
    "tributos indiretos", "compliance tributário", "obrigações acessórias",
    "apuração de tributos", "escrituração fiscal", "legislação tributária",
    "gestão de equipe", "liderança de equipe", "inglês avançado",
    "inglês intermediário", "Excel avançado", "planejamento tributário",
)


def normalize(text):
    return re.sub(r"\s+", " ", ResumeStructureService.normalize(text))


def contains(term, text):
    return bool(re.search(r"(?<!\w)" + re.escape(normalize(term)) + r"(?!\w)", normalize(text)))


def clean_description(text):
    text = html.unescape(text or "")
    text = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", "", text, flags=re.I)
    text = re.sub(r"</?(?:p|li|div|br|h[1-6])\b[^>]*>", "\n", text, flags=re.I)
    return re.sub(r"[^\S\n]+", " ", re.sub(r"<[^>]+>", "", text)).strip()


def requirements(description):
    detected = [*SkillDetector().detectar(description)]
    detected.extend(term for term in MARKET_TERMS if contains(term, description))
    output: list[str] = []
    for term in sorted(set(detected), key=lambda item: (-len(item), item.casefold())):
        if not any(contains(term, existing) for existing in output):
            output.append(term)
    return output


def source_lines(structure):
    for section in structure.get("sections", []):
        for item in section.get("items", []):
            for clause in re.split(r"[.;\n]+", item.get("text", "")):
                if clause.strip():
                    yield section.get("key", "additional"), clause.strip()
    for line in structure.get("header", []):
        for clause in re.split(r"[.;\n]+", line):
            if clause.strip():
                yield "header", clause.strip()


def evidence_for(term, structure, confirmation=None):
    occurrences = []
    for section, clause in source_lines(structure):
        if not contains(term, clause):
            continue
        text = normalize(clause)
        # Conservative within the clause: contradictory or unscoped negatives need review.
        negative = re.search(r"\b(?:sem|nao|nunca)\b", text)
        course = section in {"courses", "education", "certifications"} or re.search(
            r"\b(?:curso|academia|estud[oa]|treinamento|certificacao|certificado)\b", text
        )
        action = re.search(
            r"\b(?:apuracao|apurei|entrega|escrituracao|concilia\w*|utiliz\w*|uso de|"
            r"executei|desenvolvi|implementei|implantei|configurei|integrei|atuei|"
            r"experiencia em|experiencia com|responsavel|resolvi|liderei|conduzi)\b", text
        )
        kind = "negativa" if negative else "curso" if course else "experiencia" if action else "mencao"
        occurrences.append({"origem": "curriculo", "secao": section, "trecho": clause, "tipo_experiencia": kind})
    types = {entry["tipo_experiencia"] for entry in occurrences}
    if "negativa" in types and "experiencia" in types:
        kind = "conflito"
    else:
        kind = next((key for key in ("negativa", "experiencia", "curso", "mencao") if key in types), "ausente")
    selected = next((entry for entry in occurrences if entry["tipo_experiencia"] == kind), None)
    if kind == "conflito":
        selected = occurrences[0]
    confirmed_gap = bool(confirmation and confirmation.get("estado") == "lacuna" and confirmation.get("fonte"))
    status = "Lacuna confirmada" if confirmed_gap else {
        "experiencia": "Evidência profissional", "negativa": "Negativa explícita",
        "curso": "Curso / formação", "mencao": "Menção a validar", "ausente": "Não informado",
        "conflito": "Evidências conflitantes",
    }[kind]
    return {
        "competencia": term, "origem": "curriculo", "trecho": selected["trecho"] if selected else "",
        "tipo_experiencia": kind, "confirmacao_usuario": confirmation,
        "ocorrencias": occurrences, "status": status,
        "experiencia_sustentada": kind == "experiencia" and not confirmed_gap,
    }


def inventory(description, extra_terms=()):
    """Retém cada trecho, inclusive o que o vocabulário não sabe avaliar."""
    text = clean_description(description)
    terms = requirements(text)
    terms.extend(term for term in extra_terms if term and contains(term, text) and not any(contains(term, t) for t in terms))
    category = "A confirmar"
    rows = []
    scaffolding = set("a o as os de do da dos das e em com para no na nos nas vaga exige exigimos requisito requisitos obrigatorio obrigatorios desejavel desejaveis diferencial diferenciais preferencial necessario necessarios conhecimento conhecimentos experiencia dominio ter possuir busca buscamos profissional".split())
    for clause in re.split(r"[\n;.!?]+|(?=\b(?:Obrigat[oó]ri[oa]s?|Desej[aá]ve(?:l|is)|Condi[çc][õo]es)\s*:)", text, flags=re.I):
        clause = clause.strip(" •-*:\t")
        if not clause:
            continue
        norm = normalize(clause)
        if re.search(r"\b(?:desejave\w*|diferencia\w*|preferencial)\b", norm):
            category = "Desejável"
        elif re.search(r"\b(?:requisitos?|obrigatori\w*|exige|exigimos|necessari\w*)\b", norm):
            category = "Obrigatório"
        condition = bool(re.search(r"\b(?:condicoes|presencial|hibrid\w*|remot\w*|salario|remuneracao|clt|pj|cooperativa|jornada|viage\w*|localizacao|disponibilidade)\b", norm))
        found = [term for term in terms if contains(term, clause)]
        residual = norm
        for term in found:
            residual = re.sub(r"(?<!\w)" + re.escape(normalize(term)) + r"(?!\w)", " ", residual)
        remainder = [word for word in residual.split() if word not in scaffolding]
        # Section headings do not masquerade as requirements.
        if not found and not remainder:
            continue
        rows.append({"trecho": clause, "categoria": "Condição" if condition else category,
                     "competencias": found, "pendencias": remainder,
                     "avaliacao_parcial": condition or bool(remainder) or not found})
    return {"competencias": terms, "trechos": rows,
            "trechos_analisados": len(rows),
            "trechos_parciais": sum(row["avaliacao_parcial"] for row in rows),
            "limitacao": "Inventário heurístico de trechos, não garantia de extração de todos os requisitos; revise o anúncio integral."}


def matrix(description, structure, confirmations=None, extra_terms=()):
    scope = inventory(description, extra_terms)
    rows = []
    for term in scope["competencias"]:
        evidence = evidence_for(term, structure, (confirmations or {}).get(normalize(term)))
        categories = {row["categoria"] for row in scope["trechos"] if term in row["competencias"]}
        priority = next((value for value in ("Obrigatório", "A confirmar", "Desejável", "Condição") if value in categories), "A confirmar")
        rows.append({**evidence, "requisito": term, "prioridade": priority,
                     "evidencia": evidence["trecho"] or "Sem evidência no currículo",
                     "fonte": ("Usuário — " + evidence["confirmacao_usuario"]["fonte"])
                     if evidence["confirmacao_usuario"] else "Currículo — " + evidence["tipo_experiencia"],
                     "acao": "Destacar como experiência relatada" if evidence["experiencia_sustentada"] else "Confirmar antes de incluir"})
    return rows, scope

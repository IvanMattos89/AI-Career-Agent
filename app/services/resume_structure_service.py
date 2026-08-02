"""Estrutura currículos sem descartar nenhuma linha extraída do arquivo original."""

import re
import unicodedata


class ResumeStructureService:
    """Reconhece seções brasileiras comuns e mantém conteúdo desconhecido intacto."""

    SECTION_ALIASES = {
        "objective": {"objetivo", "objetivo profissional", "objetivos profissionais"},
        "summary": {
            "resumo", "resumo profissional", "perfil", "perfil profissional",
            "sintese", "sintese profissional", "sintese de qualificacoes",
            "qualificacoes", "qualificacoes profissionais", "sobre mim",
        },
        "skills": {
            "competencias", "competencias tecnicas", "competencias centrais",
            "habilidades", "habilidades tecnicas", "conhecimentos tecnicos",
        },
        "experience": {
            "experiencia", "experiencia profissional", "experiencias profissionais",
            "historico profissional", "trajetoria profissional",
        },
        "education": {
            "formacao", "formacao academica", "educacao", "escolaridade",
        },
        "courses": {
            "cursos", "cursos complementares", "cursos e certificacoes",
            "formacao complementar",
        },
        "certifications": {"certificacoes", "certificados", "certificacoes profissionais"},
        "technologies": {
            "tecnologias", "sistemas", "sistemas e tecnologias", "ferramentas",
            "informatica", "conhecimentos em sistemas",
        },
        "languages": {"idioma", "idiomas", "linguas"},
        "additional": {
            "informacoes adicionais", "outras informacoes", "atividades adicionais",
            "projetos", "publicacoes", "premios", "voluntariado",
        },
    }
    DISPLAY_TITLES = {
        "objective": "OBJETIVO PROFISSIONAL",
        "summary": "RESUMO PROFISSIONAL",
        "skills": "COMPETÊNCIAS CENTRAIS",
        "experience": "EXPERIÊNCIA PROFISSIONAL",
        "education": "FORMAÇÃO ACADÊMICA",
        "courses": "CURSOS E CERTIFICAÇÕES",
        "certifications": "CERTIFICAÇÕES",
        "technologies": "SISTEMAS E TECNOLOGIAS",
        "languages": "IDIOMAS",
        "additional": "INFORMAÇÕES ADICIONAIS",
    }
    COMPETENCY_LABELS = {
        "tributos": "Tributos",
        "obrigacoes": "Obrigações",
        "sistemas": "Sistemas",
        "tecnologia": "Tecnologia",
        "outras competencias": "Outras competências",
    }

    @staticmethod
    def normalize(value):
        value = unicodedata.normalize("NFKD", str(value or ""))
        value = "".join(char for char in value if not unicodedata.combining(char))
        return re.sub(r"[^a-z0-9 ]+", " ", value.casefold()).strip()

    @classmethod
    def section_key(cls, line):
        normalized = cls.normalize(line)
        normalized = re.sub(r"\s+", " ", normalized)
        if len(normalized) > 45:
            return None
        for key, aliases in cls.SECTION_ALIASES.items():
            if normalized in aliases:
                return key
        return None

    @staticmethod
    def item_kind(line):
        stripped = line.strip()
        if re.match(r"^[•●▪◦\-*–—]\s+", stripped):
            return "bullet"
        if re.search(r"\b(?:19|20)\d{2}\b", stripped) and len(stripped) < 140:
            return "position"
        return "paragraph"

    @classmethod
    def from_text(cls, text):
        header = []
        sections = []
        current = None
        for raw_line in str(text or "").splitlines():
            line = re.sub(r"\s+", " ", raw_line).strip().strip("|").strip()
            if not line:
                continue
            key = cls.section_key(line)
            if key:
                current = {
                    "key": key,
                    "title": cls.DISPLAY_TITLES[key],
                    "source_title": line,
                    "items": [],
                }
                sections.append(current)
            elif current is None:
                header.append(line)
            else:
                competency = None
                if current["key"] == "skills" and ":" in line:
                    raw_label, raw_text = line.split(":", 1)
                    label = cls.COMPETENCY_LABELS.get(cls.normalize(raw_label))
                    if label and raw_text.strip():
                        competency = {
                            "text": raw_text.strip(),
                            "label": label,
                            "kind": "competency_group",
                        }
                current["items"].append(
                    competency or {"text": line, "kind": cls.item_kind(line)}
                )

        # Um currículo sem títulos reconhecíveis continua íntegro: somente a
        # primeira linha é tratada como nome e todo o restante vira conteúdo.
        if not sections and header:
            candidate = header[0]
            words = candidate.split()
            looks_like_name = (
                2 <= len(words) <= 6
                and not re.search(r"[@\d|]", candidate)
                and not any(term in cls.normalize(candidate) for term in (
                    "experiencia", "analista", "consultor", "especialista", "formacao",
                    "competencia", "responsavel", "atuacao",
                ))
            )
            body = header[1:] if looks_like_name else header
            header = header[:1] if looks_like_name else []
            sections.append({
                "key": "additional",
                "title": "INFORMAÇÕES PROFISSIONAIS",
                "source_title": "",
                "items": [{"text": line, "kind": cls.item_kind(line)} for line in body],
            })
        return {"header": header, "sections": sections}

    @staticmethod
    def all_lines(structure):
        lines = list(structure.get("header", []))
        for section in structure.get("sections", []):
            if section.get("source_title"):
                lines.append(section["source_title"])
            lines.extend(item["text"] for item in section.get("items", []))
        return lines

    @classmethod
    def to_text(cls, structure):
        lines = list(structure.get("header", []))
        for section in structure.get("sections", []):
            lines.append(section.get("title") or section.get("source_title") or "SEÇÃO")
            for item in section.get("items", []):
                if item.get("kind") == "competency_group" and item.get("label"):
                    lines.append(f"{item['label']}: {item['text']}")
                else:
                    lines.append(item["text"])
        return "\n".join(lines)

"""Adaptação verificável de currículo a uma vaga, sempre baseada em evidências."""

import copy
import html
import json
import re
import unicodedata

from app.ai.skill_detector import SkillDetector
from app.database.sqlite_db import Database
from app.services.resume_structure_service import ResumeStructureService


class ResumeAdaptationService:
    """Cria uma versão direcionada sem alterar fatos nem o arquivo original."""

    MARKET_TERMS = (
        "SAP S/4HANA", "SAP ECC", "Tax One", "Synchro", "Mastersaf",
        "tributos indiretos", "compliance tributário", "obrigações acessórias",
        "apuração de tributos", "escrituração fiscal", "legislação tributária",
        "gestão de equipe", "liderança de equipe", "inglês avançado",
        "inglês intermediário", "Excel avançado", "planejamento tributário",
    )
    COMPETENCY_CATEGORIES = {
        "Tributos": (
            "icms", "icms st", "ipi", "pis", "cofins", "iss", "ibs", "cbs",
            "tributos indiretos", "reforma tributaria", "simples nacional",
            "lucro real", "lucro presumido",
        ),
        "Obrigações": (
            "efd", "sped", "gia", "dctf", "reinf", "dirf", "esocial",
            "obrigacoes acessorias", "escrituracao fiscal",
        ),
        "Sistemas": (
            "sap", "mastersaf", "tax one", "ktax", "synchro", "totvs",
            "protheus", "oracle", "erp",
        ),
        "Tecnologia": (
            "excel", "power bi", "sql", "python", "integracao", "tax technology",
            "automacao", "dados",
        ),
    }
    COMPETENCY_SYNONYMS = {
        "sped fiscal": "efd icms ipi",
    }

    def __init__(self):
        self.db = Database()

    @staticmethod
    def _list(value):
        return [item.strip() for item in (value or "").split(";") if item.strip()]

    @staticmethod
    def _clean_description(value):
        text = html.unescape(value or "")
        text = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", " ", text, flags=re.I)
        text = re.sub(r"<[^>]+>", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _contains(term, text):
        normalized_term = ResumeStructureService.normalize(term)
        normalized_text = ResumeStructureService.normalize(text)
        return bool(re.search(r"(?<!\w)" + re.escape(normalized_term) + r"(?!\w)", normalized_text))

    @classmethod
    def _requirements(cls, description):
        detected = list(SkillDetector().detectar(description))
        for term in cls.MARKET_TERMS:
            if cls._contains(term, description):
                detected.append(term)
        # Mantém a forma mais específica quando uma expressão já inclui outra.
        ordered = sorted(set(detected), key=lambda item: (-len(item), item.casefold()))
        output: list[str] = []
        for item in ordered:
            if any(cls._contains(item, existing) and item.casefold() != existing.casefold() for existing in output):
                continue
            output.append(item)
        return output

    @classmethod
    def _evidence_matrix(cls, description, structure):
        lines = []
        for section in structure.get("sections", []):
            for item in section.get("items", []):
                lines.append((section.get("key", "additional"), item["text"]))
        lines.extend(("header", line) for line in structure.get("header", []))
        matrix = []
        normalized_description = ResumeStructureService.normalize(description)
        for requirement in cls._requirements(description):
            evidence = [(section, line) for section, line in lines if cls._contains(requirement, line)]
            position = normalized_description.find(ResumeStructureService.normalize(requirement))
            context = normalized_description[max(0, position - 70):position + len(requirement) + 70]
            priority = "Desejável" if any(word in context for word in ("desejavel", "diferencial", "preferencial")) else "Obrigatório"
            if evidence:
                section, line = evidence[0]
                source = {
                    "experience": "Experiência profissional",
                    "education": "Formação acadêmica",
                    "courses": "Cursos e certificações",
                    "technologies": "Sistemas e tecnologias",
                    "languages": "Idiomas",
                }.get(section, "Currículo")
                status, action = "Comprovado", "Destacar"
            else:
                line, source = "Sem evidência no currículo", "Não identificado"
                status, action = "Não comprovado", "Não incluir; confirmar com o candidato"
            matrix.append({
                "requisito": requirement,
                "prioridade": priority,
                "status": status,
                "evidencia": line,
                "fonte": source,
                "acao": action,
            })
        return matrix

    @staticmethod
    def _directed_title(analysis, job_title, aligned):
        current = (analysis["cargo"] or "Profissional").strip()
        seniority = (analysis["senioridade"] or "").strip()
        target = (job_title or "").strip()
        # Senioridade ou função superior só entra quando já está comprovada na análise.
        if target:
            elevated = any(term in target.casefold() for term in ("senior", "sênior", "especialista", "coordenador", "gerente", "consultor"))
            proven_level = any(term in seniority.casefold() for term in ("sênior", "senior", "especialista", "coordenador", "gerente", "diretor"))
            role = target if not elevated or proven_level else current
        else:
            role = current
        suffix = " | ".join(aligned[:3])
        return f"{role} | {suffix}" if suffix else role

    @classmethod
    def _group_competencies(cls, items):
        groups: dict[str, list[str]] = {
            name: [] for name in cls.COMPETENCY_CATEGORIES
        }
        groups["Outras competências"] = []
        candidates, seen = [], set()
        for value in items:
            value = re.sub(r"^[•●▪◦\-*–—]\s+", "", str(value)).strip()
            normalized = ResumeStructureService.normalize(value)
            if not value or normalized in seen:
                continue
            seen.add(normalized)
            candidates.append((value, normalized))
        specific: list[tuple[str, str]] = []
        generic_terms = {"sap", "efd", "sped", "excel", "erp", "sistema", "sistemas"}
        for value, normalized in sorted(candidates, key=lambda item: len(item[1]), reverse=True):
            canonical = cls.COMPETENCY_SYNONYMS.get(normalized, normalized)
            if any(
                cls.COMPETENCY_SYNONYMS.get(existing, existing) == canonical
                for _, existing in specific
            ):
                continue
            if normalized in generic_terms and any(
                re.search(r"(?<!\w)" + re.escape(normalized) + r"(?!\w)", existing)
                for _, existing in specific
            ):
                continue
            specific.append((value, normalized))
        match_order = ("Obrigações", "Sistemas", "Tecnologia", "Tributos")
        for value, normalized in specific:
            category = "Outras competências"
            for name in match_order:
                terms = cls.COMPETENCY_CATEGORIES[name]
                if any(re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", normalized) for term in terms):
                    category = name
                    break
            groups[category].append(value)
        if groups["Tributos"]:
            groups["Outras competências"] = [
                value for value in groups["Outras competências"]
                if ResumeStructureService.normalize(value) not in {"tributo", "tributos"}
            ]
        return {name: values for name, values in groups.items() if values}

    @classmethod
    def _adapt_structure(cls, structure, summary, title, proven_skills):
        adapted = copy.deepcopy(structure)
        header = adapted.get("header", [])
        previous_titles: list[str] = []
        if header:
            contacts: list[str] = []
            for line in header[1:]:
                normalized = ResumeStructureService.normalize(line)
                if any(term in normalized for term in (
                    "cpf", "rg ", "registro geral", "estado civil", "data de nascimento",
                    "casado", "casada", "solteiro", "solteira", "cep ", "endereco",
                    "rua ", "avenida ",
                )):
                    continue
                is_contact = (
                    "@" in line or sum(char.isdigit() for char in line) >= 5
                    or bool(re.search(
                        r"(?:/|\s[-,]\s*)(?:AC|AL|AP|AM|BA|CE|DF|ES|GO|MA|MT|MS|MG|PA|PB|PR|PE|PI|RJ|RN|RS|RO|RR|SC|SP|SE|TO)\b",
                        line,
                        flags=re.I,
                    ))
                    or any(term in normalized for term in (
                        "linkedin", "telefone", "celular", "email", "crc", "brasil",
                    ))
                )
                contact_line = line.replace("📱", " | ").replace("📍", "").replace("✉", "")
                clean_line = "".join(
                    char for char in contact_line
                    if unicodedata.category(char) not in {"So", "Sk"} and char != "\ufe0f"
                ).strip(" |•-").strip()
                if clean_line:
                    (contacts if is_contact else previous_titles).append(clean_line)
            adapted["header"] = [header[0], title, *contacts]
        summary_section = next((item for item in adapted["sections"] if item["key"] == "summary"), None)
        if summary_section:
            summary_section["title"] = "RESUMO PROFISSIONAL"
            summary_section["items"].insert(0, {"text": summary, "kind": "paragraph", "generated": True})
        else:
            adapted["sections"].insert(0, {
                "key": "summary", "title": "RESUMO PROFISSIONAL", "source_title": "",
                "items": [{"text": summary, "kind": "paragraph", "generated": True}],
            })
        # O título direcionado já aparece imediatamente sob o nome. A seção
        # "Objetivo" seria redundante e é substituída por esse posicionamento.
        adapted["sections"] = [
            section for section in adapted["sections"] if section["key"] != "objective"
        ]
        technical_sections = [
            section for section in adapted["sections"]
            if section["key"] in {"skills", "technologies"}
        ]
        technical_items = [
            item["text"] for section in technical_sections for item in section.get("items", [])
        ]
        technical_items.extend(proven_skills)
        groups = cls._group_competencies(technical_items)
        grouped_items = [
            {"text": " | ".join(values), "label": name, "kind": "competency_group"}
            for name, values in groups.items()
        ]
        adapted["sections"] = [
            section for section in adapted["sections"]
            if section["key"] not in {"skills", "technologies"}
        ]
        if grouped_items:
            summary_index = next(
                (index for index, section in enumerate(adapted["sections"]) if section["key"] == "summary"),
                -1,
            )
            adapted["sections"].insert(summary_index + 1, {
                "key": "skills", "title": "COMPETÊNCIAS", "source_title": "",
                "items": grouped_items,
            })
        return adapted

    def preparar(self, descricao_vaga, titulo_vaga=None):
        description = self._clean_description(descricao_vaga)
        if not description:
            raise ValueError("Cole uma descrição de vaga antes de adequar o currículo.")
        analysis = self.db.obter_analise_ativa()
        if not analysis:
            raise RuntimeError("Analise um currículo antes de gerar uma versão adaptada.")
        resume = self.db.obter_curriculo(analysis["resume_id"])
        if not resume:
            raise RuntimeError("O currículo original não foi encontrado no banco local.")
        try:
            structure = json.loads(resume["structured_json"] or "{}")
        except (json.JSONDecodeError, TypeError):
            structure = {}
        if not structure.get("sections"):
            structure = ResumeStructureService.from_text(resume["texto"])

        matrix = self._evidence_matrix(description, structure)
        aligned = [item["requisito"] for item in matrix if item["status"] == "Comprovado"]
        missing = [item["requisito"] for item in matrix if item["status"] != "Comprovado"]
        role_title = self._directed_title(analysis, titulo_vaga, aligned)
        area = analysis["area"] or "sua área de atuação"
        experience = int(analysis["anos_experiencia"] or 0)
        experience_text = f" com {experience} anos de experiência" if experience else ""
        focus = ", ".join(aligned[:5])
        summary = (
            f"{analysis['cargo'] or 'Profissional'}{experience_text} "
            f"com atuação na área de {area}."
        )
        if focus:
            summary += f" Experiência comprovada no currículo em {focus}, priorizada para esta oportunidade."
        proven_skills = list(dict.fromkeys(
            self._list(analysis["hard_skills"]) + self._list(analysis["tecnologias"])
        ))
        document = self._adapt_structure(
            structure, summary, role_title, proven_skills
        )
        total_requirements = max(len(matrix), 1)
        coverage = len(aligned) / total_requirements
        expected_sections = {"experience", "education", "skills"}
        original_sections = {section["key"] for section in structure.get("sections", [])}
        adapted_sections = {section["key"] for section in document.get("sections", [])}
        original_structure = len(expected_sections & original_sections) / len(expected_sections)
        adapted_structure = len(expected_sections & adapted_sections) / len(expected_sections)
        target = ResumeStructureService.normalize(titulo_vaga or "")
        original_positioning = 1 if target and target in ResumeStructureService.normalize(" ".join(structure.get("header", []))) else 0
        adapted_positioning = 1 if target and target in ResumeStructureService.normalize(role_title) else 0
        ats_before = round(coverage * 75 + original_structure * 15 + original_positioning * 10)
        ats_after = round(coverage * 75 + adapted_structure * 15 + adapted_positioning * 10)
        warnings = []
        if missing:
            warnings.append(f"{len(missing)} requisito(s) sem evidência não foram incluídos no currículo.")
        if len(ResumeStructureService.to_text(document)) > 9000:
            warnings.append("Currículo extenso: revise a prévia para manter preferencialmente até duas páginas.")
        return {
            "vaga": titulo_vaga or "Vaga selecionada",
            "curriculo": analysis["nome_arquivo"],
            "titulo_direcionado": role_title,
            "resumo_direcionado": summary,
            "competencias_alinhadas": aligned,
            "palavras_revisar": missing,
            "matriz_evidencias": matrix,
            "documento": document,
            "texto_previa": ResumeStructureService.to_text(document),
            "texto_original": resume["texto"],
            "alertas": warnings,
            "score_ats": {
                "antes": ats_before,
                "depois": ats_after,
                "criterios": "75% requisitos comprovados, 15% estrutura e 10% posicionamento do título.",
            },
            "aviso": "Revise esta versão antes de enviar. O currículo original não foi alterado.",
        }

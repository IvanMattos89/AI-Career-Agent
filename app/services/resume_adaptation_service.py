"""Adaptação verificável de currículo a uma vaga, sempre baseada em evidências."""

import copy
import re
import unicodedata

from app.ai.seniority_engine import assess as assess_seniority
from app.database.sqlite_db import Database
from app.services.evidence_service import (
    MARKET_TERMS,
    clean_description,
    evidence_for,
    matrix,
    requirements,
)
from app.services.resume_structure_service import ResumeStructureService


class ResumeAdaptationService:
    """Cria uma versão direcionada sem alterar fatos nem o arquivo original."""

    MARKET_TERMS = MARKET_TERMS
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
        return clean_description(value)

    @staticmethod
    def _contains(term, text):
        normalized_term = ResumeStructureService.normalize(term)
        normalized_text = ResumeStructureService.normalize(text)
        return bool(re.search(r"(?<!\w)" + re.escape(normalized_term) + r"(?!\w)", normalized_text))

    @classmethod
    def _requirements(cls, description):
        return requirements(description)

    @classmethod
    def _evidence_matrix(cls, description, structure, confirmations=None):
        return matrix(description, structure, confirmations)[0]

    @staticmethod
    def _directed_title(analysis, job_title, aligned):
        current = (analysis["cargo"] or "Profissional").strip()
        seniority = (analysis["senioridade"] or "").strip()
        target = (job_title or "").strip()
        # Senioridade ou função superior só entra quando já está comprovada na análise.
        if target:
            elevated = any(term in target.casefold() for term in ("senior", "sênior", "especialista", "coordenador", "gerente", "consultor"))
            proven_level = any(term in seniority.casefold() for term in ("sênior", "senior", "especialista", "coordenador", "gerente", "diretor"))
            changes_role = any(term in target.casefold() and term not in current.casefold()
                               for term in ("consultor", "especialista", "coordenador", "gerente"))
            role = target if (not elevated or proven_level) and not changes_role else current
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
        declarations = [text for text in technical_items if text not in proven_skills]
        technical_items = list(proven_skills)
        if declarations:
            adapted["sections"].append({
                "key": "additional", "title": "DECLARAÇÕES DO CURRÍCULO A VALIDAR", "source_title": "",
                "items": [{"text": text, "kind": "paragraph"} for text in declarations],
            })
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
        structure = ResumeStructureService.from_text(resume["texto"])

        confirmations = self.db.listar_confirmacoes_competencias(analysis["resume_id"])
        evidence_structure = ResumeStructureService.from_text(resume["texto"])
        evidence_matrix, scope = matrix(description, evidence_structure, confirmations)
        aligned = [item["requisito"] for item in evidence_matrix if item["experiencia_sustentada"]]
        missing = [item["requisito"] for item in evidence_matrix if not item["experiencia_sustentada"]]
        current_assessment = assess_seniority(resume["texto"])
        verified_analysis = {**dict(analysis), "senioridade": current_assessment["nivel"]}
        role_title = self._directed_title(verified_analysis, titulo_vaga, aligned)
        area = analysis["area"] or "sua área de atuação"
        experience = current_assessment["anos"]
        experience_text = f" com {experience} anos de experiência" if experience else ""
        focus = ", ".join(aligned[:5])
        summary = (
            f"{analysis['cargo'] or 'Profissional'}{experience_text} "
            f"com atuação na área de {area}."
        )
        if focus:
            summary += f" Experiência relatada no currículo em {focus}, priorizada para esta oportunidade."
        proven_skills = [term for term in requirements(resume["texto"])
                         if evidence_for(term, evidence_structure, confirmations.get(ResumeStructureService.normalize(term)))["experiencia_sustentada"]]
        document = self._adapt_structure(structure, summary, role_title, proven_skills)
        from app.ai.ats_score import calculate
        ats_before = calculate({"texto_curriculo": resume["texto"]})
        ats_after = calculate({"texto_curriculo": ResumeStructureService.to_text(document)})
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
            "matriz_evidencias": evidence_matrix,
            "inventario_requisitos": scope,
            "documento": document,
            "texto_previa": ResumeStructureService.to_text(document),
            "texto_original": resume["texto"],
            "alertas": warnings,
            "score_ats": {
                "antes": ats_before,
                "depois": ats_after,
                "criterios": "Completude de cinco seções documentais, 20 pontos cada; não mede aderência ou experiência.",
            },
            "aviso": "Revise esta versão antes de enviar. O currículo original não foi alterado.",
        }

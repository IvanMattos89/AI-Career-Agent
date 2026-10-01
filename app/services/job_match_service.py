import json
import math
import re

from app.ai.analyzer import ResumeAnalyzer
from app.ai.logging_config import logger
from app.ai.skill_detector import SkillDetector
from app.database.sqlite_db import Database
from app.prompts.job_match_prompt import criar_prompt
from app.services.evidence_service import clean_description, matrix, normalize
from app.services.resume_structure_service import ResumeStructureService


class JobMatchService:
    """Compara a última análise de currículo com uma vaga e mantém o histórico."""

    def __init__(self):
        self.db = Database()
        self.analyzer = ResumeAnalyzer()

    @staticmethod
    def limpar_descricao(descricao):
        return clean_description(descricao)

    @staticmethod
    def _normalizar_lista(lista):
        if not lista:
            return []
        resultado = []
        for item in lista:
            if isinstance(item, dict):
                item = item.get("nome") or item.get("descricao") or item.get("texto") or ", ".join(map(str, item.values()))
            item = str(item).strip()
            if item:
                resultado.append(item)
        seen = set()
        unique = []
        for item in resultado:
            if item.casefold() not in seen:
                unique.append(item)
                seen.add(item.casefold())
        return unique

    @staticmethod
    def _lista_de_texto(valor):
        return [item.strip() for item in (valor or "").split(";") if item.strip()]

    def _comparar_localmente(self, analise, vaga, texto_curriculo=""):
        habilidades = self._lista_de_texto(analise["hard_skills"]) + self._lista_de_texto(analise["tecnologias"])
        habilidades = list(dict.fromkeys(habilidades))
        requisitos = SkillDetector().detectar(vaga)
        evidencia = " ".join((texto_curriculo, *habilidades)).lower()
        encontradas = [
            item for item in requisitos
            if re.search(r"(?<!\w)" + re.escape(item.lower()) + r"(?!\w)", evidencia)
        ]
        return {
            "compatibilidade": None,
            "competencias_encontradas": encontradas,
            "competencias_faltantes": [],
            "competencias_nao_informadas": [item for item in requisitos if item not in encontradas],
            "recomendacoes": ["Valide evidências dos requisitos e as condições da oportunidade."],
            "explicacao": "Comparação local de menções; não comprova domínio ou nível de proficiência.",
            "resumo": "Comparação local sem uso de IA.",
        }

    @staticmethod
    def _validar_resultado(resultado):
        if not isinstance(resultado, dict):
            raise ValueError("Job Match deve retornar um objeto.")
        if "compatibilidade" not in resultado:
            raise ValueError("Pontuação ausente.")
        score = resultado.get("compatibilidade")
        if score is not None and (
            isinstance(score, bool) or not isinstance(score, (int, float))
            or not math.isfinite(score) or not 0 <= score <= 100
        ):
            raise ValueError("Pontuação inválida.")
        for field in ("competencias_encontradas", "competencias_faltantes", "recomendacoes"):
            value = resultado.get(field)
            if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
                raise ValueError(f"Lista inválida: {field}")
        unknown = resultado.get("competencias_nao_informadas", [])
        if not isinstance(unknown, list) or any(not isinstance(item, str) for item in unknown):
            raise ValueError("Pendências inválidas.")
        for field in ("explicacao", "resumo"):
            if not isinstance(resultado.get(field), str):
                raise ValueError(f"Texto inválido: {field}")
        return resultado

    def comparar(self, descricao_vaga, titulo=None, revisao=None):
        descricao_vaga = self.limpar_descricao(descricao_vaga)
        if not descricao_vaga:
            raise ValueError("A descrição da vaga não contém texto utilizável.")

        analise = self.db.obter_analise_ativa()
        if analise is None:
            raise RuntimeError("Nenhum currículo analisado foi encontrado.")

        obter_curriculo = getattr(self.db, "obter_curriculo", None)
        curriculo = obter_curriculo(analise["resume_id"]) if obter_curriculo else None
        contexto = {
            "cargo": analise["cargo"] or "", "area": analise["area"] or "",
            "senioridade": analise["senioridade"] or "", "hard_skills": analise["hard_skills"] or "",
            "soft_skills": analise["soft_skills"] or "", "tecnologias": analise["tecnologias"] or "",
            "idiomas": analise["idiomas"] or "", "certificacoes": analise["certificacoes"] or "",
            "resumo": analise["resumo"] or "", "vaga": descricao_vaga,
            "trajetoria": (curriculo["texto"] if curriculo else "")[:14000],
        }

        if self.analyzer.llm.disponivel():
            try:
                resposta = self.analyzer.comparar(criar_prompt(contexto), timeout=20).strip()
                resposta = re.sub(r"^```(?:json)?\s*|\s*```$", "", resposta, flags=re.I)
                resultado = self._validar_resultado(json.loads(resposta))
            except (Exception,):
                # Falhas de rede, timeout ou JSON inválido não devem impedir a
                # comparação. O resultado local é salvo e deixa a interface útil.
                logger.warning("Job Match por IA indisponível; usando comparação local.")
                resultado = self._comparar_localmente(
                    analise, descricao_vaga, curriculo["texto"] if curriculo else ""
                )
        else:
            resultado = self._comparar_localmente(
                analise, descricao_vaga, curriculo["texto"] if curriculo else ""
            )

        revisao = revisao or {}
        notes = str(revisao.get("evidencia", "")).strip()
        gaps = revisao.get("lacunas_confirmadas", []) if notes else []
        if not isinstance(gaps, list) or any(not isinstance(item, str) for item in gaps):
            raise ValueError("Informe lacunas como uma lista de competências.")
        confirmations = self.db.listar_confirmacoes_competencias(analise["resume_id"])
        for skill in gaps:
            self.db.registrar_confirmacao_competencia(analise["resume_id"], skill, "lacuna", notes)
            confirmations[normalize(skill)] = {"estado": "lacuna", "fonte": notes}
        extra_terms = self._normalizar_lista([
            *resultado["competencias_encontradas"], *resultado["competencias_faltantes"],
            *resultado.get("competencias_nao_informadas", []), *gaps,
        ])
        structure = ResumeStructureService.from_text(curriculo["texto"] if curriculo else "")
        records, scope = matrix(descricao_vaga, structure, confirmations, extra_terms)
        confirmed = [row["requisito"] for row in records if row["experiencia_sustentada"]]
        missing = [row["requisito"] for row in records if row["status"] == "Lacuna confirmada"]
        unknown = [row["requisito"] for row in records if row["requisito"] not in confirmed + missing]
        resultado["matriz_evidencias"] = records
        resultado["inventario_requisitos"] = scope
        resultado["evidencias"] = [f"{row['requisito']} — {row['status']}: {row['evidencia']}" for row in records]
        resultado["abrangencia"] = [
            f"{row['categoria']}: {row['trecho']} — "
            + ("avaliação parcial; confirmar escopo e condições" if row["avaliacao_parcial"] else "termos reconhecidos; validar evidências")
            for row in scope["trechos"]
        ]
        resultado["competencias_encontradas"] = confirmed
        resultado["competencias_nao_informadas"] = unknown
        resultado["competencias_faltantes"] = missing
        partial = bool(scope["trechos_parciais"]) or not scope["trechos"]
        resultado["compatibilidade"] = (
            round(len(confirmed) / (len(confirmed) + len(missing)) * 100)
            if (confirmed or missing) and not unknown and not partial else None
        )
        resultado["explicacao"] = (
            f"{len(confirmed)} competências com experiência relatada; {len(unknown)} a validar; "
            f"{len(missing)} lacunas confirmadas. {scope['trechos_parciais']} de "
            f"{scope['trechos_analisados']} trechos têm avaliação parcial. "
            "A pontuação só aparece quando todos os trechos reconhecidos estão avaliados. "
            "Não estima contratação ou domínio profissional. " + scope["limitacao"]
        )
        evidence = str(revisao.get("evidencia", "")).strip()
        state = revisao.get("condicoes", "pendentes")
        if state == "incompativeis" and evidence:
            decision = "descartar"
            reason = "Incompatibilidade confirmada pelo usuário: " + evidence
            next_step = "Reconsiderar apenas se a condição documentada mudar."
        elif state == "alinhadas" and evidence and confirmed and not unknown and not missing and not partial:
            decision = "priorizar"
            reason = "Requisitos identificados com evidência e condições validadas pelo usuário: " + evidence
            next_step = "Validar a profundidade das experiências e preparar candidatura; enviar só com autorização."
        else:
            decision = "investigar"
            reason = "Há requisitos, condições ou profundidade da evidência a validar; desconhecido não significa lacuna."
            next_step = "Confirmar pendências, escopo, crescimento, regime, remuneração e condições desejadas."
        resultado.update(recomendacao=decision, justificativa=reason, proximo_passo=next_step)
        resultado["revisao"] = revisao
        resultado["resumo"] = f"{decision.capitalize()}: {reason} Próximo passo: {next_step}"
        resultado["id"] = self.db.salvar_job_match(analise["resume_id"], descricao_vaga, resultado, titulo=titulo)
        resultado["descricao_vaga"] = descricao_vaga
        resultado["curriculo"] = analise["nome_arquivo"]
        return resultado

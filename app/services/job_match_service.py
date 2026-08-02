import json
import re
from html import unescape

from app.ai.analyzer import ResumeAnalyzer
from app.ai.logging_config import logger
from app.ai.skill_detector import SkillDetector
from app.database.sqlite_db import Database
from app.prompts.job_match_prompt import criar_prompt


class JobMatchService:
    """Compara a última análise de currículo com uma vaga e mantém o histórico."""

    def __init__(self):
        self.db = Database()
        self.analyzer = ResumeAnalyzer()

    @staticmethod
    def limpar_descricao(descricao):
        texto = unescape(descricao or "")
        texto = re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", " ", texto, flags=re.I)
        texto = re.sub(r"<[^>]+>", " ", texto)
        return re.sub(r"\s+", " ", texto).strip()

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
        return list(dict.fromkeys(resultado))

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
        faltantes = [item for item in requisitos if item not in encontradas]
        base = requisitos
        score = round((len(encontradas) / max(len(base), 1)) * 100)
        return {
            "compatibilidade": score,
            "competencias_encontradas": encontradas,
            "competencias_faltantes": faltantes,
            "recomendacoes": ["Inclua evidências práticas das competências mais importantes da vaga."],
            "explicacao": "Estimativa local baseada nas competências identificadas na vaga e comprovadas no currículo.",
            "resumo": "Comparação local concluída sem uso do modelo de IA.",
        }

    def comparar(self, descricao_vaga, titulo=None):
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
                resultado = json.loads(resposta)
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

        for chave in ("competencias_encontradas", "competencias_faltantes", "recomendacoes"):
            resultado[chave] = self._normalizar_lista(resultado.get(chave, []))
        evidence_text = " ".join((
            curriculo["texto"] if curriculo else "",
            analise["hard_skills"] or "",
            analise["tecnologias"] or "",
            analise["idiomas"] or "",
            analise["certificacoes"] or "",
        ))
        confirmed, rejected = [], []
        for skill in resultado["competencias_encontradas"]:
            if re.search(r"(?<!\w)" + re.escape(skill) + r"(?!\w)", evidence_text, flags=re.I):
                confirmed.append(skill)
            else:
                rejected.append(skill)
        resultado["competencias_encontradas"] = confirmed
        resultado["competencias_faltantes"] = list(dict.fromkeys(
            [*resultado["competencias_faltantes"], *rejected]
        ))
        resultado["compatibilidade"] = max(0, min(100, int(float(resultado.get("compatibilidade", 0)))))
        evaluated = len(confirmed) + len(resultado["competencias_faltantes"])
        if evaluated:
            evidence_cap = round(len(confirmed) / evaluated * 100)
            resultado["compatibilidade"] = min(resultado["compatibilidade"], evidence_cap)
        resultado["explicacao"] = str(resultado.get("explicacao") or resultado.get("resumo") or "A nota considera a aderência entre experiência, competências e requisitos da vaga.")
        resultado["id"] = self.db.salvar_job_match(analise["resume_id"], descricao_vaga, resultado, titulo=titulo)
        resultado["descricao_vaga"] = descricao_vaga
        resultado["curriculo"] = analise["nome_arquivo"]
        return resultado

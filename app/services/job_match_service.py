import json
import re
from html import unescape

from app.ai.analyzer import ResumeAnalyzer
from app.ai.logging_config import logger
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

    def _comparar_localmente(self, analise, vaga):
        habilidades = self._lista_de_texto(analise["hard_skills"]) + self._lista_de_texto(analise["tecnologias"])
        habilidades = list(dict.fromkeys(habilidades))
        vaga_lower = vaga.lower()
        encontradas = [item for item in habilidades if re.search(r"(?<!\w)" + re.escape(item.lower()) + r"(?!\w)", vaga_lower)]
        score = round((len(encontradas) / max(len(habilidades), 1)) * 100)
        return {
            "compatibilidade": score,
            "competencias_encontradas": encontradas,
            "competencias_faltantes": [],
            "recomendacoes": ["Inclua evidências práticas das competências mais importantes da vaga."],
            "explicacao": "Estimativa local baseada nas competências do currículo encontradas na descrição da vaga.",
            "resumo": "Comparação local concluída sem uso do modelo de IA.",
        }

    def comparar(self, descricao_vaga, titulo=None):
        descricao_vaga = self.limpar_descricao(descricao_vaga)
        if not descricao_vaga:
            raise ValueError("A descrição da vaga não contém texto utilizável.")

        analise = self.db.obter_ultima_analise()
        if analise is None:
            raise RuntimeError("Nenhum currículo analisado foi encontrado.")

        contexto = {
            "cargo": analise["cargo"] or "", "area": analise["area"] or "",
            "senioridade": analise["senioridade"] or "", "hard_skills": analise["hard_skills"] or "",
            "soft_skills": analise["soft_skills"] or "", "tecnologias": analise["tecnologias"] or "",
            "idiomas": analise["idiomas"] or "", "certificacoes": analise["certificacoes"] or "",
            "resumo": analise["resumo"] or "", "vaga": descricao_vaga,
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
                resultado = self._comparar_localmente(analise, descricao_vaga)
        else:
            resultado = self._comparar_localmente(analise, descricao_vaga)

        for chave in ("competencias_encontradas", "competencias_faltantes", "recomendacoes"):
            resultado[chave] = self._normalizar_lista(resultado.get(chave, []))
        resultado["compatibilidade"] = max(0, min(100, int(float(resultado.get("compatibilidade", 0)))))
        resultado["explicacao"] = str(resultado.get("explicacao") or resultado.get("resumo") or "A nota considera a aderência entre experiência, competências e requisitos da vaga.")
        resultado["id"] = self.db.salvar_job_match(analise["resume_id"], descricao_vaga, resultado, titulo=titulo)
        resultado["descricao_vaga"] = descricao_vaga
        resultado["curriculo"] = analise["nome_arquivo"]
        return resultado

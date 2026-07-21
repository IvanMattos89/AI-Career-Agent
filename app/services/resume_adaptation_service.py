import re

from app.database.sqlite_db import Database
from app.services.job_match_service import JobMatchService


class ResumeAdaptationService:
    """Monta uma versão revisável do currículo, sem alterar o original."""

    def __init__(self):
        self.db = Database()

    @staticmethod
    def _lista(valor):
        return [item.strip() for item in (valor or "").split(";") if item.strip()]

    def preparar(self, descricao_vaga, titulo_vaga=None):
        descricao = JobMatchService.limpar_descricao(descricao_vaga)
        if not descricao:
            raise ValueError("Cole uma descrição de vaga antes de adequar o currículo.")
        analise = self.db.obter_ultima_analise()
        if not analise:
            raise RuntimeError("Analise um currículo antes de gerar uma versão adaptada.")
        curriculo = self.db.obter_curriculo(analise["resume_id"])
        if not curriculo:
            raise RuntimeError("O currículo original não foi encontrado no banco local.")
        competencias = list(dict.fromkeys(self._lista(analise["hard_skills"]) + self._lista(analise["tecnologias"])))
        texto_vaga = descricao.lower()
        alinhadas = [item for item in competencias if re.search(r"(?<!\w)" + re.escape(item.lower()) + r"(?!\w)", texto_vaga)]
        alvo = titulo_vaga or "Vaga selecionada"
        destaque = ", ".join(alinhadas[:6] or competencias[:6]) or "competências descritas no currículo"
        resumo = (
            f"{analise['cargo'] or 'Profissional'} com atuação em {analise['area'] or 'sua área de especialidade'}, "
            f"com foco em {destaque}. Perfil direcionado para a oportunidade de {alvo}."
        )
        return {
            "vaga": alvo,
            "curriculo": analise["nome_arquivo"],
            "resumo_direcionado": resumo,
            "competencias_alinhadas": alinhadas,
            "palavras_revisar": [item for item in competencias if item not in alinhadas],
            "texto_original": curriculo["texto"],
            "aviso": "Revise esta versão antes de enviar. O currículo original não foi alterado.",
        }

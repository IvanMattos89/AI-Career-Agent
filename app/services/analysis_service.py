from app.ai.analyzer import ResumeAnalyzer
from app.database.sqlite_db import Database


class AnalysisService:

    def __init__(self):
        self.analyzer = ResumeAnalyzer()
        self.db = Database()

    def analisar_texto(self, resume_id, texto):

        analise = self.analyzer.analisar(texto)

        self.db.salvar_analise(
            resume_id=resume_id,
            cargo=analise.cargo,
            area=analise.area,
            senioridade=analise.senioridade,
            ats_score=analise.ats_score,
            hard_skills="; ".join(analise.hard_skills),
            soft_skills="; ".join(analise.soft_skills),
            tecnologias="; ".join(analise.tecnologias),
            idiomas="; ".join(analise.idiomas),
            certificacoes="; ".join(analise.certificacoes),
            anos_experiencia=analise.anos_experiencia,
            nivel_curriculo=analise.nivel_curriculo,
            palavras_chave="; ".join(analise.palavras_chave),
            pontos_fortes="; ".join(analise.pontos_fortes),
            pontos_melhoria="; ".join(analise.pontos_melhoria),
            competencias_faltantes="; ".join(analise.competencias_faltantes),
            recomendacoes="; ".join(analise.recomendacoes),
            resumo=analise.resumo,
        )

        return analise

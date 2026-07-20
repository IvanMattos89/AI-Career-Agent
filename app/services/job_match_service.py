import json

from app.database.sqlite_db import Database
from app.ai.analyzer import ResumeAnalyzer
from app.prompts.job_match_prompt import criar_prompt


class JobMatchService:

    def __init__(self):

        self.db = Database()
        self.analyzer = ResumeAnalyzer()


    def comparar(self, descricao_vaga):

        historico = self.db.listar_historico()

        if not historico:
            raise Exception("Nenhum currículo analisado foi encontrado.")

        ultimo = historico[0]

        analise = self.db.obter_analise(ultimo["id"])

        if analise is None:
            raise Exception("Não foi encontrada análise para o currículo.")

        contexto = {

            "cargo": analise["cargo"] or "",
            "area": analise["area"] or "",
            "senioridade": analise["senioridade"] or "",
            "hard_skills": analise["hard_skills"] or "",
            "soft_skills": analise["soft_skills"] or "",
            "tecnologias": analise["tecnologias"] or "",
            "idiomas": analise["idiomas"] or "",
            "certificacoes": analise["certificacoes"] or "",
            "resumo": analise["resumo"] or "",
            "vaga": descricao_vaga

        }

        prompt = criar_prompt(contexto)

        resposta = self.analyzer.comparar(prompt)

        try:

            return json.loads(resposta)

        except Exception:

            raise Exception(
                "A IA retornou uma resposta inválida.\n\n"
                + resposta
            )


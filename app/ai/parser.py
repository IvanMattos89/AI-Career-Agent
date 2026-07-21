import json

import re

from app.ai.validator import validate
from app.ai.normalizer import normalize
from app.ai.ats_score import calculate
from app.ai.models import ResumeAnalysis


def parse_resume_analysis(resposta):

    if isinstance(resposta, bytes):
        resposta = resposta.decode("utf8")

    resposta = re.sub(r"^```(?:json)?\s*|\s*```$", "", resposta.strip(), flags=re.I)

    dados = json.loads(resposta)
    if not isinstance(dados, dict):
        raise ValueError("A resposta da IA deve ser um objeto JSON.")

    dados = validate(dados)

    dados = normalize(dados)

    ats = calculate(dados)

    return ResumeAnalysis(

        cargo=dados["cargo"],

        area=dados["area"],

        confianca=dados["confianca"],

        senioridade=dados["senioridade"],

        hard_skills=dados["hard_skills"],

        soft_skills=dados["soft_skills"],

        tecnologias=dados["tecnologias"],

        idiomas=dados["idiomas"],

        certificacoes=dados["certificacoes"],

        anos_experiencia=dados.get("anos_experiencia", 0),

        nivel_curriculo=dados.get("nivel_curriculo", ""),

        palavras_chave=dados.get("palavras_chave", []),

        pontos_fortes=dados.get("pontos_fortes", []),

        pontos_melhoria=dados.get("pontos_melhoria", []),

        competencias_faltantes=dados.get("competencias_faltantes", []),

        recomendacoes=dados.get("recomendacoes", []),

        resumo=dados["resumo"],

        ats_score=ats
    )

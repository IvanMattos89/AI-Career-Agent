import json

from app.ai.validator import validate
from app.ai.normalizer import normalize
from app.ai.ats_score import calculate
from app.ai.models import ResumeAnalysis


def parse_resume_analysis(resposta):

    if isinstance(resposta, bytes):
        resposta = resposta.decode("utf8")

    resposta = resposta.strip()

    dados = json.loads(resposta)

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

        resumo=dados["resumo"],

        ats_score=ats
    )

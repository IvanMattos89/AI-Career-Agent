from app.ai.llm_client import LLMClient
from app.ai.logging_config import logger
from app.ai.models import ResumeAnalysis
from app.ai.ats_score import calculate
from app.ai.prompts import RESUME_ANALYSIS_PROMPT
from app.ai.parser import parse_resume_analysis
from app.ai.skill_detector import SkillDetector


class ResumeAnalyzer:
    def __init__(self):
        self.llm = LLMClient()
        self.skill_detector = SkillDetector()

    def analisar(self, texto):
        try:
            prompt = RESUME_ANALYSIS_PROMPT.format(curriculo=texto)
            return parse_resume_analysis(self.llm.perguntar(prompt))
        except Exception as erro:
            # Indisponibilidade do provedor é um caminho previsto: a interface
            # continua funcional com análise local sem imprimir dados sensíveis.
            logger.warning("Análise por IA indisponível; usando fallback local: %s", erro)
            return self._analise_local(texto)

    def _analise_local(self, texto):
        texto_lower = texto.lower()
        cargo, area = "Profissão não identificada", "Não identificada"
        mapa = {
            "analista fiscal": ("Analista Fiscal", "Fiscal e Tributária"),
            "assistente fiscal": ("Assistente Fiscal", "Fiscal e Tributária"),
            "contador": ("Contador", "Contabilidade"),
            "analista financeiro": ("Analista Financeiro", "Financeiro"),
            "desenvolvedor": ("Desenvolvedor de Software", "Tecnologia"),
            "programador": ("Programador", "Tecnologia"),
            "analista de dados": ("Analista de Dados", "Dados"),
            "cientista de dados": ("Cientista de Dados", "Dados"),
            "engenheiro civil": ("Engenheiro Civil", "Engenharia"),
            "advogado": ("Advogado", "Jurídico"),
        }
        for chave, valor in mapa.items():
            if chave in texto_lower:
                cargo, area = valor
                break
        skills = self.skill_detector.detectar(texto)
        resumo = "Análise local baseada no conteúdo do currículo. Conecte um provedor de IA para obter recomendações detalhadas."
        ats = calculate({"cargo": cargo if cargo != "Profissão não identificada" else "", "area": area if area != "Não identificada" else "", "senioridade": "Em análise", "hard_skills": skills, "tecnologias": skills, "idiomas": [], "certificacoes": [], "resumo": resumo})
        recomendacoes = [
            "Inclua resultados mensuráveis nas experiências mais relevantes.",
            "Adapte o resumo profissional às palavras-chave da vaga antes de candidatar.",
        ]
        if not skills:
            recomendacoes.append("Descreva ferramentas, sistemas e tributos com os quais você trabalhou.")
        return ResumeAnalysis(
            cargo=cargo, area=area, confianca=0.60, senioridade="Em análise",
            hard_skills=skills, tecnologias=skills, palavras_chave=skills,
            pontos_fortes=skills[:5], recomendacoes=recomendacoes,
            resumo=resumo, ats_score=ats,
        )

    def comparar(self, prompt, timeout=None):
        return self.llm.perguntar(prompt, timeout=timeout)

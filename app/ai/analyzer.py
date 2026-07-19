import traceback

from app.ai.llm_client import LLMClient
from app.ai.models import ResumeAnalysis
from app.ai.prompts import RESUME_ANALYSIS_PROMPT
from app.ai.parser import parse_resume_analysis
from app.ai.skill_detector import SkillDetector


class ResumeAnalyzer:

    def __init__(self):
        self.llm = LLMClient()
        self.skill_detector = SkillDetector()

    def analisar(self, texto):

        if self.llm.disponivel():
            try:
                prompt = RESUME_ANALYSIS_PROMPT.format(curriculo=texto)

                resposta = self.llm.perguntar(prompt)

                print("=" * 80)
                print("TIPO DA RESPOSTA:", type(resposta))
                print("RESPOSTA RECEBIDA:")
                print(repr(resposta))
                print("=" * 80)

                return parse_resume_analysis(resposta)

            except Exception:
                print("=" * 80)
                print("ERRO DA IA")
                print("=" * 80)
                traceback.print_exc()
                print("=" * 80)
                print("Utilizando análise local...")

        return self._analise_local(texto)

    def _analise_local(self, texto):

        texto_lower = texto.lower()

        cargo = "Profissão não identificada"
        area = "Não identificada"

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
            "advogado": ("Advogado", "Jurídico")
        }

        for chave, valor in mapa.items():
            if chave in texto_lower:
                cargo = valor[0]
                area = valor[1]
                break

        skills = self.skill_detector.detectar(texto)

        return ResumeAnalysis(
            cargo=cargo,
            area=area,
            confianca=0.60,
            senioridade="Em análise",
            hard_skills=skills,
            soft_skills=[],
            tecnologias=skills,
            idiomas=[],
            certificacoes=[],
            resumo="Análise local baseada no conteúdo do currículo."
        )

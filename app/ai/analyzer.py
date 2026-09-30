import re
import unicodedata

from app.ai.ats_score import assess as assess_completeness
from app.ai.ats_score import calculate
from app.ai.llm_client import LLMClient
from app.ai.logging_config import logger
from app.ai.models import ResumeAnalysis
from app.ai.parser import parse_resume_analysis
from app.ai.professions import PROFESSIONS
from app.ai.prompts import RESUME_ANALYSIS_PROMPT
from app.ai.seniority_engine import assess as assess_seniority
from app.ai.seniority_engine import estimate as estimar_senioridade
from app.ai.seniority_engine import experience_years
from app.ai.skill_detector import SkillDetector


class ResumeAnalyzer:
    PERFIS = {
        "Analista Fiscal": ("Fiscal e Tributária", ("analista fiscal", "analista tributario", "tributar", "fiscal")),
        "Assistente Fiscal": ("Fiscal e Tributária", ("assistente fiscal",)),
        "Contador": ("Contabilidade", ("contador", "contabil")),
        "Analista Financeiro": ("Financeiro", ("analista financeiro", "financeiro", "fp&a", "fpa")),
        "Desenvolvedor de Software": ("Tecnologia", ("desenvolvedor", "programador", "software engineer", "software developer")),
        "Analista de Dados": ("Dados", ("analista de dados", "data analyst", "cientista de dados", "business intelligence")),
        "Engenheiro Civil": ("Engenharia", ("engenheiro civil",)),
        "Advogado": ("Jurídico", ("advogado", "juridico")),
    }
    def __init__(self):
        self.llm = LLMClient()
        self.skill_detector = SkillDetector()

    def analisar(self, texto):
        try:
            prompt = RESUME_ANALYSIS_PROMPT.format(curriculo=texto)
            return self._avaliacao_documental(parse_resume_analysis(self.llm.perguntar(prompt)), texto)
        except Exception as erro:
            # Indisponibilidade do provedor é um caminho previsto: a interface
            # continua funcional com análise local sem imprimir dados sensíveis.
            logger.warning("Análise por IA indisponível; usando fallback local: %s", erro)
            return self._analise_local(texto)

    def _analise_local(self, texto):
        texto_normalizado = self._normalizar(texto)
        cargo, area, pontos_cargo = self._identificar_perfil(texto_normalizado)
        skills = self.skill_detector.detectar(texto)
        for habilidade in PROFESSIONS.get(cargo, {}).get("skills", []):
            if self._normalizar(habilidade) in texto_normalizado:
                skills.append(habilidade)
        skills = sorted(set(skills), key=str.casefold)
        idiomas = self._detectar_idiomas(texto_normalizado)
        certificacoes = self._detectar_certificacoes(texto_normalizado)
        anos = self._anos_experiencia(texto)
        senioridade = estimar_senioridade(texto)
        confianca = min(0.95, 0.35 + pontos_cargo * 0.12 + min(len(skills), 8) * 0.03)
        resumo = (
            "Análise local baseada em cargos, competências e sinais de experiência encontrados no currículo. "
            "Conecte um provedor de IA para recomendações mais detalhadas."
        )
        ats = calculate({"texto_curriculo": texto})
        recomendacoes = [
            "Inclua resultados mensuráveis nas experiências mais relevantes.",
            "Adapte o resumo profissional às palavras-chave da vaga antes de candidatar.",
        ]
        if not skills:
            recomendacoes.append("Descreva ferramentas, sistemas e tributos com os quais você trabalhou.")
        if not idiomas:
            recomendacoes.append("Informe idiomas e nível de proficiência quando forem relevantes para as vagas desejadas.")
        return self._avaliacao_documental(ResumeAnalysis(
            cargo=cargo, area=area, confianca=round(confianca, 2), senioridade=senioridade,
            hard_skills=skills, tecnologias=skills, idiomas=idiomas, certificacoes=certificacoes,
            anos_experiencia=anos, palavras_chave=skills,
            pontos_fortes=skills[:5], recomendacoes=recomendacoes,
            resumo=resumo, ats_score=ats,
        ), texto)

    @staticmethod
    def _normalizar(texto):
        texto = unicodedata.normalize("NFKD", texto or "")
        return "".join(caractere for caractere in texto if not unicodedata.combining(caractere)).casefold()

    def _identificar_perfil(self, texto):
        melhor = ("Profissão não identificada", "Não identificada", 0)
        inicio = texto[:1800]
        for cargo, (area, aliases) in self.PERFIS.items():
            pontos = sum(
                len(re.findall(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", texto))
                for alias in aliases
            )
            pontos += sum(2 for alias in aliases if alias in inicio)
            if pontos > melhor[2]:
                melhor = (cargo, area, pontos)
        return melhor

    @staticmethod
    def _anos_experiencia(texto):
        return experience_years(texto)

    @staticmethod
    def _avaliacao_documental(result, texto):
        seniority = assess_seniority(texto)
        completeness = assess_completeness({"texto_curriculo": texto})
        result.senioridade = seniority["nivel"]
        result.anos_experiencia = seniority["anos"]
        result.ats_score = completeness["pontuacao"]
        result.avaliacao = {"senioridade": seniority, "completude": completeness}
        return result

    @staticmethod
    def _detectar_idiomas(texto):
        idiomas = {"ingles": "Inglês", "espanhol": "Espanhol", "frances": "Francês", "alemao": "Alemão"}
        return [
            nome for termo, nome in idiomas.items()
            if re.search(r"(?<!\w)" + termo + r"(?!\w)", texto)
        ]

    @staticmethod
    def _detectar_certificacoes(texto):
        patterns = {
            "CRC": r"(?<!\w)crc(?!\w)",
            "PMP": r"(?<!\w)pmp(?!\w)",
            "CPA": r"(?<!\w)cpa(?:[- ]?\d{2})?(?!\w)",
            "AWS Certified": r"(?<!\w)aws certified(?!\w)",
            "Certificação SAP": (
                r"(?<!\w)(?:certificacao|certificado)\s+(?:em\s+)?sap(?!\w)"
            ),
        }
        return [name for name, pattern in patterns.items() if re.search(pattern, texto)]

    def comparar(self, prompt, timeout=None):
        return self.llm.perguntar(prompt, timeout=timeout)

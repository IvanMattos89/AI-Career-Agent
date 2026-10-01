import json
import re

from app.ai.llm_client import LLMClient
from app.database.sqlite_db import Database
from app.services.evidence_service import evidence_for, normalize, requirements
from app.services.resume_structure_service import ResumeStructureService


class CareerAssistantService:
    """Camada V2 para conversa, treino de entrevista e plano de carreira."""

    def __init__(self, resume_id=None):
        self.db = Database()
        self.llm = LLMClient()
        self.resume_id = resume_id if resume_id is not None else self.db.obter_curriculo_ativo_id()

    def _perfil(self):
        profile_id = getattr(self, "resume_id", None)
        analysis = self.db.obter_analise(profile_id) if profile_id is not None else self.db.obter_analise_ativa()
        if not analysis:
            raise ValueError("Selecione e analise um currículo antes de usar o assistente.")
        return analysis

    def _contexto(self, analysis):
        resume_id = analysis["resume_id"]
        resume = self.db.obter_curriculo(resume_id)
        if not resume:
            raise ValueError("O currículo desta conversa foi excluído.")
        structure = ResumeStructureService.from_text(resume["texto"])
        confirmations = self.db.listar_confirmacoes_competencias(resume_id)
        records = [evidence_for(term, structure, confirmations.get(normalize(term)))
                   for term in requirements(resume["texto"])]
        return (
            f"Perfil: {resume_id}\nCargo: {analysis['cargo'] or '-'}\nÁrea: {analysis['area'] or '-'}\n"
            "Os registros abaixo são declarações do currículo, não verificação externa. "
            "Curso, menção, negativa e conflito não comprovam experiência.\n"
            + json.dumps(records, ensure_ascii=False)
        )

    def conversar(self, pergunta):
        pergunta = (pergunta or "").strip()
        if not pergunta:
            raise ValueError("Digite uma pergunta para o assistente.")
        analysis = self._perfil()
        resume_id = analysis["resume_id"]
        contexto = self._contexto(analysis)
        history_reader = getattr(self.db, "listar_mensagens_assistente", None)
        messages = history_reader(limite=10, resume_id=resume_id) if history_reader else []
        history = "\n".join(f"{row['role']}: {row['content'][:1500]}" for row in reversed(messages))
        objective_reader = getattr(self.db, "obter_objetivo_carreira", None)
        objective = objective_reader(resume_id) if objective_reader else ""
        resposta = None
        if self.llm.disponivel():
            prompt = (
                "Você é um orientador de carreira. Responda em português, de forma prática, "
                "sem inventar fatos sobre a pessoa. Use o contexto abaixo e sugira próximos passos claros.\n\n"
                "Use o histórico para continuidade; respostas anteriores da IA não são fatos verificados. "
                "Informação ausente é pendência, não falta de competência. "
                "Conclua análises de vaga com recomendação, justificativa e próximo passo.\n"
                f"OBJETIVO INFORMADO\n{objective[:2000]}\nHISTÓRICO RECENTE\n{history}\n"
                f"CONTEXTO\n{contexto}\n\nPERGUNTA\n{pergunta}"
            )
            try:
                resposta = self.llm.perguntar(prompt, json_mode=False, timeout=12).strip()
            except Exception:
                # A disponibilidade pode mudar entre o teste e a chamada; a
                # Central continua útil sem depender de provedor externo.
                resposta = None
        if not resposta:
            resposta = (
                "O modo local está ativo. Com base no seu perfil, comece por transformar "
                "as experiências mais relevantes em resultados verificáveis, quantitativos ou qualitativos. "
                "Valide informações ausentes antes de definir lacunas de desenvolvimento.\n\n"
                f"Sua pergunta: {pergunta}"
            )
        self.db.salvar_mensagem_assistente("user", pergunta, resume_id)
        self.db.salvar_mensagem_assistente("assistant", resposta, resume_id)
        return resposta

    def proxima_pergunta(self, tema):
        contexto = self._contexto(self._perfil())
        if self.llm.disponivel():
            prompt = (
                "Crie UMA pergunta de entrevista em português, objetiva e realista. "
                f"Tema: {tema}. Use o perfil abaixo; retorne somente a pergunta.\n\n{contexto}"
            )
            try:
                pergunta = self.llm.perguntar(prompt, json_mode=False, timeout=12).strip()
                if pergunta:
                    return pergunta
            except Exception:
                pass
        perguntas = {
            "Técnica": "Conte sobre um problema técnico complexo que você resolveu. Qual foi sua abordagem e o resultado?",
            "Comportamental": "Descreva uma situação em que recebeu um feedback difícil e como agiu a partir dele.",
            "RH": "Por que esta oportunidade representa o próximo passo adequado para sua carreira?",
        }
        return perguntas.get(tema, perguntas["RH"])

    def avaliar_resposta(self, pergunta, resposta, tema):
        resume_id = self._perfil()["resume_id"]
        if not (resposta or "").strip():
            raise ValueError("Informe uma resposta para avaliação.")
        feedback = (
            "Avaliação indisponível no modo local. Organize a resposta em situação, tarefa, "
            "ação e resultado verificável, quantitativo ou qualitativo. Nenhuma nota foi atribuída."
        )
        nota = None
        if self.llm.disponivel():
            prompt = (
                "Avalie esta resposta de entrevista de 0 a 100. Na primeira linha use 'NOTA: N'. "
                "Justifique com evidências de contexto, responsabilidade pessoal, ação e resultado; "
                "aceite resultados qualitativos verificáveis. Não invente métricas.\n"
                f"Tema: {tema}\nPergunta: {pergunta}\nResposta: {resposta}"
            )
            try:
                candidate = self.llm.perguntar(prompt, json_mode=False, timeout=12).strip()
                match = re.match(r"NOTA:\s*(\d{1,3})\s*\n(.+)", candidate, re.I | re.S)
                if match and 0 <= int(match.group(1)) <= 100 and match.group(2).strip():
                    nota, feedback = int(match.group(1)), candidate
            except Exception:
                pass
        self.db.salvar_entrevista(pergunta, resposta, feedback, nota, tema, resume_id)
        return {"nota": nota, "feedback": feedback}

    def plano_de_acao(self):
        analise = self._perfil()
        if not analise:
            return ["Importe e analise um currículo para gerar um plano personalizado."]
        itens = []
        for item in (analise["recomendacoes"] or "").split(";"):
            if item.strip():
                itens.append(item.strip())
        for item in (analise["competencias_faltantes"] or "").split(";"):
            if item.strip():
                itens.append(f"Valide em vaga relevante ou entrevista antes de planejar estudo: {item.strip()}")
        return (itens or ["Revise o currículo e registre resultados verificáveis, inclusive qualitativos."])[:6]

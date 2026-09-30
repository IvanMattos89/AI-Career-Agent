import re

from app.ai.llm_client import LLMClient
from app.database.sqlite_db import Database


class CareerAssistantService:
    """Camada V2 para conversa, treino de entrevista e plano de carreira."""

    def __init__(self):
        self.db = Database()
        self.llm = LLMClient()

    def _contexto(self):
        analise = self.db.obter_analise_ativa()
        if not analise:
            return "Ainda não há currículo analisado. Oriente o usuário a importar e analisar um currículo."
        return (
            f"Cargo: {analise['cargo'] or '-'}\nÁrea: {analise['area'] or '-'}\n"
            f"Senioridade: {analise['senioridade'] or '-'}\nHard skills: {analise['hard_skills'] or '-'}\n"
            f"Pontos de melhoria: {analise['pontos_melhoria'] or '-'}\n"
            f"Competências a validar (ausência no currículo não comprova lacuna): {analise['competencias_faltantes'] or '-'}\n"
            f"Resumo: {analise['resumo'] or '-'}"
        )

    def conversar(self, pergunta):
        pergunta = (pergunta or "").strip()
        if not pergunta:
            raise ValueError("Digite uma pergunta para o assistente.")
        contexto = self._contexto()
        history_reader = getattr(self.db, "listar_mensagens_assistente", None)
        messages = history_reader(limite=10) if history_reader else []
        history = "\n".join(f"{row['role']}: {row['content'][:1500]}" for row in reversed(messages))
        objective_reader = getattr(self.db, "obter_objetivo_carreira", None)
        objective = objective_reader() if objective_reader else ""
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
        self.db.salvar_mensagem_assistente("user", pergunta)
        self.db.salvar_mensagem_assistente("assistant", resposta)
        return resposta

    def proxima_pergunta(self, tema):
        contexto = self._contexto()
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
        self.db.salvar_entrevista(pergunta, resposta, feedback, nota, tema)
        return {"nota": nota, "feedback": feedback}

    def plano_de_acao(self):
        analise = self.db.obter_analise_ativa()
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

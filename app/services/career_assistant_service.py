from app.ai.llm_client import LLMClient
from app.database.sqlite_db import Database


class CareerAssistantService:
    """Camada V2 para conversa, treino de entrevista e plano de carreira."""

    def __init__(self):
        self.db = Database()
        self.llm = LLMClient()

    def _contexto(self):
        analise = self.db.obter_ultima_analise()
        if not analise:
            return "Ainda não há currículo analisado. Oriente o usuário a importar e analisar um currículo."
        return (
            f"Cargo: {analise['cargo'] or '-'}\nÁrea: {analise['area'] or '-'}\n"
            f"Senioridade: {analise['senioridade'] or '-'}\nHard skills: {analise['hard_skills'] or '-'}\n"
            f"Pontos de melhoria: {analise['pontos_melhoria'] or '-'}\n"
            f"Competências faltantes: {analise['competencias_faltantes'] or '-'}\n"
            f"Resumo: {analise['resumo'] or '-'}"
        )

    def conversar(self, pergunta):
        pergunta = (pergunta or "").strip()
        if not pergunta:
            raise ValueError("Digite uma pergunta para o assistente.")
        contexto = self._contexto()
        resposta = None
        if self.llm.disponivel():
            prompt = (
                "Você é um orientador de carreira. Responda em português, de forma prática, "
                "sem inventar fatos sobre a pessoa. Use o contexto abaixo e sugira próximos passos claros.\n\n"
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
                "as experiências mais relevantes em resultados mensuráveis e priorize as "
                "competências faltantes indicadas na última análise.\n\n"
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
        if len((resposta or "").strip()) < 20:
            feedback, nota = "Desenvolva a resposta com contexto, ação e resultado mensurável (método STAR).", 35
        elif self.llm.disponivel():
            prompt = (
                "Avalie esta resposta de entrevista de 0 a 100. Responda em português com uma nota "
                "na primeira linha no formato 'NOTA: N' e até três sugestões práticas.\n"
                f"Pergunta: {pergunta}\nResposta: {resposta}"
            )
            try:
                feedback = self.llm.perguntar(prompt, json_mode=False, timeout=12).strip()
                import re
                match = re.search(r"NOTA:\s*(\d{1,3})", feedback, re.I)
                nota = min(100, int(match.group(1))) if match else 70
            except Exception:
                feedback, nota = (
                    "O modo local está ativo. Organize a resposta em situação, tarefa, ação e resultado; "
                    "inclua uma métrica concreta e relacione a experiência ao cargo.", 70,
                )
        else:
            feedback, nota = (
                "Boa base. Para fortalecer, organize a resposta em situação, tarefa, ação e resultado; "
                "inclua uma métrica concreta e relacione a experiência ao cargo.", 70,
            )
        self.db.salvar_entrevista(pergunta, resposta, feedback, nota, tema)
        return {"nota": nota, "feedback": feedback}

    def plano_de_acao(self):
        analise = self.db.obter_ultima_analise()
        if not analise:
            return ["Importe e analise um currículo para gerar um plano personalizado."]
        itens = []
        for item in (analise["recomendacoes"] or "").split(";"):
            if item.strip():
                itens.append(item.strip())
        for item in (analise["competencias_faltantes"] or "").split(";"):
            if item.strip():
                itens.append(f"Estude ou evidencie: {item.strip()}")
        return (itens or ["Revise o currículo e inclua resultados mensuráveis."])[:6]

import json

from app.ai.llm_client import LLMClient
from app.database.sqlite_db import Database


class ApplicationStudioService:
    """Cria material de candidatura sem inventar conteúdo do currículo."""

    def __init__(self):
        self.db = Database()
        self.llm = LLMClient()

    def gerar_pacote(self, oportunidade_id):
        vaga = self.db.obter_oportunidade(oportunidade_id)
        analise = self.db.obter_ultima_analise()
        if not vaga:
            raise ValueError("Oportunidade não encontrada.")
        if not analise:
            raise ValueError("Analise um currículo antes de criar material de candidatura.")
        pacote = None
        if self.llm.disponivel():
            prompt = """Você é especialista em candidatura profissional. Crie material em português usando SOMENTE os dados abaixo; não invente experiências, resultados ou competências.
Retorne JSON válido com: carta (3 parágrafos), resumo_direcionado (até 90 palavras), palavras_chave (lista) e checklist (lista de 4 itens).

CANDIDATO
Cargo: {cargo}
Área: {area}
Senioridade: {senioridade}
Hard skills: {skills}
Tecnologias: {tecnologias}
Resumo: {resumo}

VAGA
Título: {titulo}
Empresa: {empresa}
Descrição: {descricao}""".format(
                cargo=analise["cargo"] or "", area=analise["area"] or "",
                senioridade=analise["senioridade"] or "", skills=analise["hard_skills"] or "",
                tecnologias=analise["tecnologias"] or "", resumo=analise["resumo"] or "",
                titulo=vaga["titulo"], empresa=vaga["empresa"] or "", descricao=vaga["descricao"] or "",
            )
            try:
                pacote = json.loads(self.llm.perguntar(prompt, timeout=20))
            except (Exception,):
                pacote = None
        if not pacote:
            empresa = vaga["empresa"] or "a empresa"
            cargo = analise["cargo"] or "profissional"
            skills = [x.strip() for x in (analise["hard_skills"] or "").split(";") if x.strip()]
            pacote = {
                "carta": f"Olá, equipe da {empresa}.\n\nTenho interesse na oportunidade de {vaga['titulo']}. Atuo como {cargo} e acredito que meu perfil pode contribuir para a posição.\n\nGostaria de conversar sobre como minhas experiências e competências se conectam às necessidades da vaga.",
                "resumo_direcionado": f"{cargo} com foco em {analise['area'] or 'sua área de atuação'}. Destaque no currículo: {', '.join(skills[:4]) or 'experiências relevantes'}.",
                "palavras_chave": skills[:8],
                "checklist": ["Revise a carta antes de enviar.", "Adapte o título profissional do currículo.", "Inclua resultados reais e mensuráveis.", "Confirme os requisitos obrigatórios da vaga."],
            }
        pacote = {
            "carta": str(pacote.get("carta", "")).strip(),
            "resumo_direcionado": str(pacote.get("resumo_direcionado", "")).strip(),
            "palavras_chave": [str(x) for x in pacote.get("palavras_chave", []) if str(x).strip()],
            "checklist": [str(x) for x in pacote.get("checklist", []) if str(x).strip()],
            "vaga": vaga["titulo"], "empresa": vaga["empresa"] or "",
        }
        pacote["id"] = self.db.salvar_pacote_candidatura(oportunidade_id, pacote)
        return pacote

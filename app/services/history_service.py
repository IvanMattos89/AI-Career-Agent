from app.database.sqlite_db import Database


class HistoryService:

    def __init__(self):
        self.db = Database()

    def listar_curriculos(self):
        return self.db.listar_historico()

    def obter_curriculo(self, resume_id):
        return self.db.obter_curriculo(resume_id)

    def excluir_curriculo(self, resume_id):
        self.db.excluir_curriculo(resume_id)

    def excluir_analise(self, resume_id):
        self.db.excluir_analise(resume_id)

    def remover_curriculo(self, resume_id):
        self.db.excluir_analise(resume_id)
        self.db.excluir_curriculo(resume_id)
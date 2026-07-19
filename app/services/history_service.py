from app.database.sqlite_db import Database


class HistoryService:

    def __init__(self):
        self.db = Database()

    def listar_curriculos(self):
        return self.db.listar_curriculos_completos()

    def obter_curriculo(self, curriculo_id):
        return self.db.obter_curriculo(curriculo_id)

    def excluir_curriculo(self, curriculo_id):
        self.db.excluir_curriculo(curriculo_id)

    def limpar_historico(self):
        self.db.limpar_historico()

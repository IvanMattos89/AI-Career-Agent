from app.database.sqlite_db import Database


class DashboardService:

    def __init__(self):

        self.db = Database()


    def indicadores(self):

        ultima = self.db.dashboard_ultima_analise()

        if ultima:

            cargo = ultima["cargo"]
            data = ultima["created_at"]

        else:

            cargo = "-"
            data = "-"

        match_metricas = self.db.dashboard_job_match_metricas()
        candidaturas = self.db.metricas_candidaturas()
        return {

            "ats": self.db.dashboard_media_ats(),

            "curriculos": self.db.dashboard_total_curriculos(),

            "ultima": data,

            "cargo": cargo,
            "job_matches": match_metricas["total"],
            "match_medio": match_metricas["media"],
            "candidaturas": candidaturas["total"],
            "taxa_entrevistas": candidaturas["entrevistas"],
            "acompanhamentos": candidaturas["acompanhamentos"],
            "melhor_fonte": candidaturas["melhor_fonte"],
        }


    def ultimas_analises(self):

        return self.db.dashboard_ultimas_analises()


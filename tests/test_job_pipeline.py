import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import requests

from app.database.sqlite_db import Database
from app.models.job_listing import JobListing
from app.services.job_search_service import JobSearchService


class FakeProvider:
    def __init__(self, name, jobs):
        self.name = name
        self.jobs = jobs

    def search(self, _query):
        return self.jobs


class FailingProvider:
    name = "Indisponível"

    def search(self, _query):
        raise requests.ConnectionError("falha simulada")


class JobPipelineTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.patches = [
            patch("app.database.sqlite_db.DATABASE", root / "career.db"),
            patch("app.database.sqlite_db.DATA_DIR", root),
            patch("app.database.sqlite_db.RESUMES_DIR", root / "resumes"),
        ]
        for item in self.patches:
            item.start()
        self.db = Database()

    def tearDown(self):
        self.db.close()
        for item in reversed(self.patches):
            item.stop()
        self.temp.cleanup()

    def test_search_deduplicates_providers_and_persists_decision(self):
        description = "Analista Fiscal responsável por ICMS, SPED e apuração fiscal no Brasil."
        jobs = [
            JobListing(
                title="Analista Fiscal", company="Empresa X", location="São Paulo / SP",
                url="https://one.example/jobs/123", description=description, provider="Greenhouse",
            ),
            JobListing(
                title="Analista Fiscal", company="Empresa X", location="São Paulo / SP",
                url="https://two.example/vaga/abc", description=description + " Excel.", provider="Lever",
            ),
        ]
        service = JobSearchService(
            providers=[FakeProvider("Greenhouse", jobs[:1]), FakeProvider("Lever", jobs[1:])],
            db=self.db,
        )

        result = service.buscar("Analista Fiscal", estado="SP")

        self.assertEqual(len(result), 1)
        self.assertGreater(result[0]["rank_score"], 0)
        self.db.definir_decisao_vaga(result[0]["id"], "descartada")
        self.assertEqual(service.buscar("Analista Fiscal", estado="SP"), [])

    def test_converts_listing_to_application_and_tracks_status(self):
        listing = JobListing(
            title="Analista Fiscal", company="Empresa Y", location="Curitiba / PR",
            description="Analista Fiscal com ICMS e SPED.", provider="Vagas.com",
        ).as_dict()
        listing_id, _ = self.db.salvar_vaga_encontrada(listing)

        application_id = self.db.converter_vaga_em_candidatura(listing_id)
        self.db.atualizar_candidatura(
            application_id,
            status="Candidatado",
            next_action="Cobrar retorno",
            next_action_at="2020-01-01",
        )

        application = self.db.obter_oportunidade(application_id)
        history = self.db.listar_historico_candidatura(application_id)
        metrics = self.db.metricas_candidaturas()
        self.assertEqual(application["status"], "Candidatado")
        self.assertEqual(application["next_action"], "Cobrar retorno")
        self.assertEqual(len(history), 2)
        self.assertEqual(metrics["total"], 1)
        self.assertEqual(metrics["acompanhamentos"], 1)

    def test_provider_failure_does_not_hide_results_from_other_sources(self):
        valid = JobListing(
            title="Analista Fiscal", company="Empresa Z", location="Brasil",
            description="Analista Fiscal com experiência em ICMS.", provider="Fonte pública",
        )
        service = JobSearchService(
            providers=[FailingProvider(), FakeProvider("Fonte pública", [valid])], db=self.db
        )

        result = service.buscar("Analista Fiscal")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["empresa"], "Empresa Z")


if __name__ == "__main__":
    unittest.main()

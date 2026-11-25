import sqlite3
from unittest.mock import Mock

import pytest
import requests

from app.database.requisition_identity import migrate_requisition_identity
from app.database.sqlite_db import Database
from app.models.job_listing import JobListing
from app.services.job_providers import AdzunaProvider, GupyProvider, JoobleProvider
from app.services.job_search_service import JobSearchService
from app.services.opportunity_tracking import salary_assessment


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setattr("app.database.sqlite_db.DATABASE", tmp_path / "test.db")
    monkeypatch.setattr("app.database.sqlite_db.DATA_DIR", tmp_path)
    monkeypatch.setenv("JOB_SEARCH_CACHE_MINUTES", "0")
    monkeypatch.setenv("JOB_REJECTED_TITLES", "")
    monkeypatch.setenv("JOB_SEARCH_MAX_PAGES", "3")
    database = Database()
    yield database
    database.close()


def listing(ident, description):
    return JobListing(title="Analista Fiscal Sênior", company="Empresa Exemplo", location="São Paulo/SP",
                      external_id=ident, provider="Fonte", url=f"https://jobs.example/{ident}", description=description)


def test_distinct_requisitions_survive_and_decisions_do_not_cross(db):
    first = listing("101", "Analista Fiscal Sênior de tributos diretos")
    second = listing("102", "Analista Fiscal Sênior de tributos indiretos")
    provider = Mock()
    provider.name = "Fonte"
    provider.search.return_value = [first, second]
    service = JobSearchService([provider], db)
    result = service.buscar("Analista Fiscal")
    assert len(result) == 2
    assert len({row["id"] for row in result}) == 2
    assert all(row["possible_duplicates"] == 1 for row in result)
    db.definir_decisao_vaga(result[0]["id"], "descartada")
    assert [row["id"] for row in service.buscar("Analista Fiscal")] == [result[1]["id"]]


def test_ids_are_stable_and_urls_are_fallback_not_title_signature():
    one = listing("101", "Primeiro texto")
    changed = listing("101", "Texto alterado")
    changed.title = "Especialista Fiscal"
    assert one.canonical_key == changed.canonical_key
    assert one.canonical_key != listing("102", one.description).canonical_key
    foreign = listing("101", one.description)
    foreign.provider = "Outra fonte"
    assert one.canonical_key != foreign.canonical_key
    one.external_id = changed.external_id = ""
    changed.url = one.url + "?utm_source=mail"
    assert one.canonical_key == changed.canonical_key
    changed.url = one.url + "?ref=another-requisition"
    assert one.canonical_key != changed.canonical_key
    changed.url = "https://jobs.example/another"
    assert one.canonical_key != changed.canonical_key


def test_migration_preserves_rows_links_and_marks_legacy_review():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""CREATE TABLE job_listings(id INTEGER PRIMARY KEY,title TEXT,company TEXT,location TEXT,
        provider TEXT,external_id TEXT,url TEXT,description TEXT,canonical_key TEXT UNIQUE,decision TEXT);
        CREATE TABLE notes(listing_id INTEGER REFERENCES job_listings(id), body TEXT);
        INSERT INTO job_listings VALUES (1,'Fiscal','Empresa','SP','Fonte','101','https://jobs.example/101','Diretos','old1','favorita');
        INSERT INTO job_listings VALUES (2,'Fiscal','Empresa','SP','Fonte','101','https://jobs.example/101','Indiretos','old2','descartada');
        INSERT INTO notes VALUES(2,'Histórico preservado');""")
    migrate_requisition_identity(conn.cursor())
    rows = conn.execute("SELECT * FROM job_listings ORDER BY id").fetchall()
    assert len(rows) == 2 and rows[0]["canonical_key"] != rows[1]["canonical_key"]
    assert [row["decision"] for row in rows] == ["favorita", "descartada"]
    assert all(row["identity_review"] == 1 for row in rows)
    assert conn.execute("SELECT listing_id FROM notes").fetchone()[0] == 2
    conn.close()


@pytest.mark.parametrize("minimum,expected", [(9000, True), (11000, False), (0, True)])
def test_upper_salary_is_not_a_guaranteed_floor(minimum, expected):
    result = salary_assessment("até R$ 10.000 mensais", minimum, False)
    assert result["eligible"] is expected
    assert result["min"] is None and result["max"] == 10000
    assert "A confirmar" in result["status"]


def response(payload):
    mock = Mock()
    mock.json.return_value = payload
    return mock


def gupy_item(ident, location="SP"):
    return {"id": ident, "name": "Analista Fiscal Sênior", "description": "Analista Fiscal e ICMS",
            "addressState": location, "addressCountry": "BR", "companyName": "Empresa"}


def test_gupy_pages_measure_incremental_eligible_and_keep_partial_results(db, monkeypatch):
    get = Mock(side_effect=[response({"results": [gupy_item(1)], "totalPages": 3}),
                           response({"results": [gupy_item(1), gupy_item(2), gupy_item(3, "RJ")], "totalPages": 3}),
                           requests.ConnectionError("https://secret-token.example")])
    monkeypatch.setattr("app.services.job_providers.requests.get", get)
    source = GupyProvider("secret")
    service = JobSearchService([source], db)
    jobs = service.buscar("Analista Fiscal", estado="SP")
    assert len(jobs) == 2
    assert [call.kwargs["params"]["page"] for call in get.call_args_list] == [1, 2, 3]
    report = service.last_report["fontes"][0]
    assert [page["elegiveis_unicas"] for page in report["paginas"]] == [1, 1, 0]
    assert report["status"] == "falha parcial de paginação"
    assert "secret-token" not in str(report)


def test_adzuna_pages_and_duplicate_page_stop(monkeypatch):
    monkeypatch.setenv("JOB_SEARCH_MAX_PAGES", "5")
    get = Mock(return_value=response({"count": 1000, "results": [{"id": "1", "title": "Fiscal"}]}))
    monkeypatch.setattr("app.services.job_providers.requests.get", get)
    provider = AdzunaProvider("id", "secret")
    provider.search("Fiscal")
    assert [call.args[0] for call in get.call_args_list] == [
        "https://api.adzuna.com/v1/api/jobs/br/search/1", "https://api.adzuna.com/v1/api/jobs/br/search/2"]
    assert provider.page_diagnostics[-1]["unicas"] == 0


def test_jooble_uses_brazil_domain_and_page_parameter(monkeypatch):
    monkeypatch.setenv("JOB_SEARCH_MAX_PAGES", "2")
    post = Mock(side_effect=[response({"totalCount": 100, "jobs": [{"id": 1, "title": "Fiscal"}]}),
                            response({"totalCount": 100, "jobs": [{"id": 2, "title": "Fiscal"}]})])
    monkeypatch.setattr("app.services.job_providers.requests.post", post)
    jobs = JoobleProvider("secret").search("Fiscal")
    assert len(jobs) == 2
    assert all(call.args[0].startswith("https://br.jooble.org/api/") for call in post.call_args_list)
    assert [call.kwargs["json"]["page"] for call in post.call_args_list] == [1, 2]


def test_pagination_limit_one_and_empty_page_stop(monkeypatch):
    monkeypatch.setenv("JOB_SEARCH_MAX_PAGES", "1")
    get = Mock(return_value=response({"results": [gupy_item(1)], "totalPages": 10}))
    monkeypatch.setattr("app.services.job_providers.requests.get", get)
    GupyProvider("secret").search("Fiscal")
    assert get.call_count == 1
    monkeypatch.setenv("JOB_SEARCH_MAX_PAGES", "5")
    get.reset_mock()
    get.return_value = response({"results": [], "totalPages": 10})
    assert GupyProvider("secret").search("Fiscal") == []
    assert get.call_count == 1

import json
from unittest.mock import Mock

import pytest

from app.database.sqlite_db import Database
from app.models.job_listing import JobListing
from app.services.job_location import eligible, normalize_job_location
from app.services.job_search_service import JobSearchService


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setattr("app.database.sqlite_db.DATABASE", tmp_path / "test.db")
    monkeypatch.setattr("app.database.sqlite_db.DATA_DIR", tmp_path)
    monkeypatch.setenv("JOB_TARGET_TITLES", "")
    monkeypatch.setenv("JOB_ACCEPTABLE_TITLES", "")
    monkeypatch.setenv("JOB_REJECTED_TITLES", "")
    monkeypatch.setenv("JOB_SEARCH_MAX_QUERIES", "20")
    monkeypatch.setenv("JOB_SEARCH_CACHE_MINUTES", "0")
    database = Database()
    yield database
    database.close()


@pytest.mark.parametrize("location,state,city,expected", [
    ("Campinas", "SP", "Campinas", True),
    ("Campinas-SP", "SP", "", True),
    ("Campinas", "RJ", "", False),
    ("Remoto — Brasil", "SP", "Campinas", True),
    ("Remote - Brazil", "MG", "Belo Horizonte", True),
    ("Remote - São Paulo/SP", "RJ", "", False),
    ("Híbrido - São Paulo/SP", "RJ", "", False),
    ("Remote - Argentina", "SP", "", False),
    ("Remote", "SP", "", False),
    ("Worldwide", "SP", "", False),
    ("Colombo, Portugal", "PR", "", False),
    ("Portland, OR, USA", "", "", False),
    ("Bom Jesus", "PI", "", False),
])
def test_geography_and_remote_scope(location, state, city, expected):
    assert eligible(location, state, city) is expected


def test_structured_country_overrides_homonymous_city():
    assert not eligible("Colombo", country="Sri Lanka", city="Colombo")
    assert eligible("Campinas", "SP", country="BR", city="Campinas")
    assert normalize_job_location("Campinas")["inferred_city"] is True
    assert not eligible("Brasil", "SP", work_mode="Hybrid")


def listing(company="Empresa", location="Campinas", mode="Remoto", title="Analista Fiscal"):
    return JobListing(title=title, company=company, location=location,
                      modality=mode, description=f"{title}: ICMS e SPED.")


def provider(name, jobs=None, error=None):
    item = Mock()
    item.name = name
    item.search.return_value = jobs or []
    item.search.side_effect = error
    return item


def test_diagnostic_distinguishes_config_empty_failure_and_filter(db):
    service = JobSearchService([
        provider("Vagas.com", [listing()]),
        provider("Remotive", [listing(location="Germany")]),
        provider("Adzuna"),
        provider("Jooble", error=ValueError("https://example/secret-token")),
    ], db)
    service._default_catalog = True
    assert len(service.buscar("Analista Fiscal", estado="SP")) == 1
    report = db.resumo_ultima_busca()["diagnostico"]
    sources = {item["provider"]: item for item in report["fontes"]}
    assert sources["Vagas.com"]["status"] == "resultados disponíveis"
    assert sources["Remotive"]["status"] == "resultados eliminados por filtro"
    assert sources["Remotive"]["filtros"]["localização"] == 1
    assert sources["Adzuna"]["status"] == "sem resultados"
    assert sources["Jooble"]["status"] == "falhou"
    assert sources["Greenhouse"]["status"] == "não configurada"
    assert "secret-token" not in json.dumps(report)
    assert "secret-token" not in str([dict(r) for r in db.resumo_ultima_busca()["providers"]])


def test_unknown_modality_is_opt_in_and_failures_do_not_turn_empty_into_error(db):
    service = JobSearchService([provider("Teste", [listing(mode="Não informado")]), provider("Falha", error=ValueError())], db)
    assert service.buscar("Analista Fiscal", modalidade="Remoto") == []
    assert len(service.buscar("Analista Fiscal", modalidade="Remoto", incluir_modalidade_desconhecida=True)) == 1
    assert service.last_report["fontes"][0]["provider"]  # Both reports persist.


def test_zero_results_is_success_but_total_failure_raises_with_diagnostic(db):
    service = JobSearchService([provider("Teste")], db)
    assert service.buscar("Analista Fiscal") == []
    assert service.last_report["fontes"][0]["status"] == "sem resultados"
    service.providers = [provider("Teste", error=ValueError("secret"))]
    with pytest.raises(RuntimeError, match="diagnóstico"):
        service.buscar("Analista Fiscal")
    assert service.last_report["fontes"][0]["status"] == "falhou"


def test_filters_duplicates_decisions_and_result_cap_are_separate(db):
    service = JobSearchService([provider("Teste", [
        listing("A"), listing("A"), listing("B"), listing("C"),
        listing("Modalidade", mode="Híbrido"), listing("Exterior", location="Germany"),
        listing("Irrelevante", title="Desenvolvedor Python"),
    ])], db)
    first = service.buscar("Analista Fiscal", limite=1, modalidade="Remoto")
    db.definir_decisao_vaga(first[0]["id"], "descartada")
    result = service.buscar("Analista Fiscal", limite=1, modalidade="Remoto")
    item = service.last_report["fontes"][0]
    assert len(result) == 1
    assert item["duplicadas"] == item["descartadas"] == item["limite"] == 1
    assert item["filtros"]["localização"] == item["filtros"]["modalidade"] == item["filtros"]["relevância"] == 1


def test_configured_queries_are_executed_first_and_omissions_are_visible(db, monkeypatch):
    monkeypatch.setenv("JOB_TARGET_TITLES", "Gerente de Tributos, Consultor Tax One, gerente de tributos")
    monkeypatch.setenv("JOB_ACCEPTABLE_TITLES", "Especialista Contábil")
    db.obter_analise_ativa = lambda: {"cargo": "Analista Fiscal", "hard_skills": "ICMS"}
    source = provider("Teste")
    service = JobSearchService([source], db)
    result = service.buscar_para_curriculo(max_consultas=3)
    assert [call.args[0] for call in source.search.call_args_list] == [
        "Gerente de Tributos", "Consultor Tax One", "Especialista Contábil",
    ]
    assert "Analista Fiscal" in result["consultas_omitidas"]
    report = db.resumo_ultima_busca()["diagnostico"]
    assert report["consultas"] == result["consultas_executadas"]
    assert report["fontes"][0]["consultas"] == 3


def test_report_aggregates_multiple_queries_and_partial_failure(db):
    db.obter_analise_ativa = lambda: {"cargo": "Analista Fiscal", "hard_skills": "ICMS"}
    source = provider("Teste")
    source.search.side_effect = [[listing()], ValueError("failure")]
    service = JobSearchService([source], db)
    result = service.buscar_para_curriculo(max_consultas=2)
    assert len(result["vagas"]) == 1
    source_report = service.last_report["fontes"][0]
    assert source_report["consultas"] == 2
    assert source_report["falhas"] == 1
    assert source_report["status"] == "falha parcial"
    assert source_report["exibidas"] == 1


def test_ui_shows_aggregate_report_without_interpreting_source_html(db):
    from types import SimpleNamespace

    from app.ui.pages.job_match_page import JobMatchPage

    service = JobSearchService([provider("<b>Fonte</b>")], db)
    service.buscar("Analista Fiscal")
    label = Mock()
    page = SimpleNamespace(db=db, resumo_fontes=label)
    JobMatchPage._mostrar_metricas_fontes(page)
    rendered = label.setText.call_args.args[0]
    assert "&lt;b&gt;Fonte&lt;/b&gt;" in rendered
    assert "sem resultados" in rendered
    assert "Consultas executadas" in rendered


def test_worker_forwards_unknown_modality_option_and_closes_db(monkeypatch):
    from app.ui.workers import JobSearchWorker

    service = Mock()
    service.buscar.return_value = []
    monkeypatch.setattr("app.services.job_search_service.JobSearchService", lambda: service)
    worker = JobSearchWorker("Analista Fiscal", incluir_modalidade_desconhecida=True)
    worker.run()
    assert service.buscar.call_args.kwargs["incluir_modalidade_desconhecida"] is True
    service.db.close.assert_called_once()


def test_aggregate_reports_cross_query_duplicates_and_final_cap(db):
    db.obter_analise_ativa = lambda: {"cargo": "Analista Fiscal", "hard_skills": "ICMS"}
    source = provider("Teste")
    source.search.side_effect = [[listing("A")], [listing("B", title="Analista Tributário")]]
    service = JobSearchService([source], db)
    result = service.buscar_para_curriculo(max_consultas=2, limite=1)
    assert len(result["vagas"]) == 1
    assert service.last_report["fontes"][0]["limite"] == 1

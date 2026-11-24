import csv
from datetime import date, timedelta
from unittest.mock import Mock

import pytest

from app.database.sqlite_db import Database
from app.models.job_listing import JobListing
from app.services.job_search_service import JobSearchService
from app.services.opportunity_tracking import FISCAL_QUERIES, OpportunityTracking, salary_assessment


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setattr("app.database.sqlite_db.DATABASE", tmp_path / "test.db")
    monkeypatch.setattr("app.database.sqlite_db.DATA_DIR", tmp_path)
    monkeypatch.setenv("JOB_SEARCH_CACHE_MINUTES", "0")
    monkeypatch.setenv("JOB_REJECTED_TITLES", "")
    database = Database()
    yield database
    database.close()


def job(company="Empresa", salary="R$ 8.000 a 10.000 por mês"):
    return JobListing(title="Analista Fiscal Sênior", company=company, location="Campinas", salary=salary,
                      description="Analista Fiscal Sênior com ICMS e SPED", provider="Teste")


def service(db, jobs):
    provider = Mock()
    provider.name = "Teste"
    provider.search.return_value = jobs
    return JobSearchService([provider], db)


@pytest.mark.parametrize("text,minimum,unknown,expected", [
    ("R$ 8.000 a 10.000 por mês", 9000, False, True),
    ("R$ 8.000 a 10.000 por mês", 11000, True, False),
    ("R$ 96.000 anual", 9000, True, True),
    ("R$ 96.000 anual", 9000, False, False),
    ("USD 10.000 por mês", 8000, False, False),
    ("8000 - 10000", 8000, False, False),
    ("", 8000, True, True),
    ("", 0, False, False),
    ("R$ 8.000 mensais", 8000, False, True),
    ("R$ 8 mil mensais", 8000, False, False),
    ("R$ 5.000 + R$ 1.000 de benefícios por mês", 5500, False, False),
    ("A partir de R$ 8.000 por mês", 10000, False, True),
])
def test_only_comparable_salary_is_filtered(text, minimum, unknown, expected):
    assert salary_assessment(text, minimum, unknown)["eligible"] == expected


def test_multinational_evidence_is_separate_from_match_score_and_expires(db):
    tracker = OpportunityTracking(db)
    assert not tracker.company("Empresa X", "Somos uma multinacional")["prioritize"]
    tracker.set_company("Empresa B", "confirmada", "https://company.example/about", date.today().isoformat(), "Operações em dois países")
    search = service(db, [job("Empresa A"), job("Empresa B")])
    original = search.buscar("Analista Fiscal")
    ranked = search.buscar("Analista Fiscal", priorizar_multinacionais=True)
    assert ranked[0]["empresa"] == "Empresa B"
    assert {r["empresa"]: r["rank_score"] for r in ranked} == {r["empresa"]: r["rank_score"] for r in original}
    tracker.set_company("Empresa B", "confirmada", "site", (date.today() - timedelta(days=181)).isoformat(), "Registro antigo")
    assert not tracker.company("Empresa B")["prioritize"]


def test_salary_filter_and_diagnostic(db):
    search = service(db, [job("A", "R$ 5.000 por mês"), job("B", ""), job("C")])
    results = search.buscar("Analista Fiscal", salario_minimo=8000, incluir_salario_desconhecido=False)
    assert [r["empresa"] for r in results] == ["C"]
    assert search.last_report["fontes"][0]["filtros"]["remuneração"] == 2


def test_new_repeated_closed_and_pending_are_distinct_and_absence_is_not_closure(db):
    tracker = OpportunityTracking(db)
    search = service(db, [job(), job()])
    ident = search.buscar("Analista Fiscal")[0]["id"]
    first = tracker.report()[0]
    assert first["new_count"] == 1 and first["duplicates"] == 1
    assert first["availability"] == "pendente"
    search.providers[0].search.return_value = []
    search.buscar("Analista Fiscal")
    assert tracker.availability(ident) == "pendente"
    tracker.set_availability(ident, "encerrada", "https://jobs.example/1", date.today().isoformat(), "Anúncio informa inscrições encerradas")
    search.providers[0].search.return_value = [job()]
    assert search.buscar("Analista Fiscal") == []
    row = tracker.report()[0]
    assert row["availability"] == "encerrada" and row["duplicates"] == 2
    tracker.set_availability(ident, "aberta", "fonte", (date.today() - timedelta(days=31)).isoformat(), "Aberta na data")
    assert tracker.availability(ident) == "pendente"
    with pytest.raises(ValueError):
        tracker.set_availability(ident, "encerrada", "", date.today().isoformat(), "")


def test_fiscal_queries_are_opt_in_and_include_both_career_targets(db, monkeypatch):
    db.obter_analise_ativa = lambda: {"cargo": "Analista de Dados", "hard_skills": "SQL"}
    search = service(db, [])
    monkeypatch.setenv("JOB_SEARCH_MAX_QUERIES", "20")
    normal = search.buscar_para_curriculo()
    expanded = search.buscar_para_curriculo(perfil_fiscal=True)
    assert "Especialista Tributário" not in normal["consultas_executadas"]
    assert expanded["consultas_executadas"][:len(FISCAL_QUERIES)] == FISCAL_QUERIES


def test_dashboard_pipeline_uses_actual_applications_and_active_resume(db):
    tracker = OpportunityTracking(db)
    one = db.salvar_curriculo("a", "a", "Primeiro")
    two = db.salvar_curriculo("b", "b", "Segundo")
    for resume, status in [(one, "Salva"), (one, "Entrevista com RH"), (two, "Candidatado")]:
        db.conn.execute("INSERT INTO opportunities(titulo,status,resume_id) VALUES ('Vaga',?,?)", (status, resume))
    db.conn.commit()
    assert tracker.pipeline(one) == {"oportunidades": 2, "candidaturas": 1, "entrevistas": 1}
    assert tracker.pipeline(None)["candidaturas"] == 0


def test_report_ui_filters_and_export_prevent_csv_formulas(db, tmp_path):
    from PySide6.QtWidgets import QApplication

    from app.ui.opportunity_report import OpportunityReport

    app = QApplication.instance() or QApplication([])
    search = service(db, [job("=Formula")])
    search.buscar("Analista Fiscal")
    dialog = OpportunityReport(db)
    assert dialog.table.rowCount() == 1
    dialog.kind.setCurrentIndex(3)
    assert dialog.table.rowCount() == 0
    dialog.kind.setCurrentIndex(4)
    target = tmp_path / "report.csv"
    dialog.tracker.export(target, dialog.rows)
    with target.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream, delimiter=";"))
    assert rows[0]["company"] == "'=Formula"
    assert rows[0]["availability"] == "pendente"
    dialog.close()
    assert app is not None

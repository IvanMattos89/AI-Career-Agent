import json
import sqlite3
from unittest.mock import Mock

import pytest

from app.ai.ats_score import calculate
from app.database.sqlite_db import Database
from app.services.career_assistant_service import CareerAssistantService
from app.services.job_match_service import JobMatchService


def service_for(payload=None, text="Apuração de ICMS em SAP."):
    service = JobMatchService.__new__(JobMatchService)
    service.db = Mock()
    service.db.obter_analise_ativa.return_value = dict(
        resume_id=1, nome_arquivo="cv.txt", cargo="Analista Fiscal", area="Fiscal",
        senioridade="", hard_skills="ICMS", tecnologias="", soft_skills="",
        idiomas="", certificacoes="", resumo="",
    )
    service.db.obter_curriculo.return_value = {"texto": text}
    service.db.salvar_job_match.return_value = 1
    service.db.listar_confirmacoes_competencias.return_value = {}
    service.analyzer = Mock()
    service.analyzer.llm.disponivel.return_value = payload is not None
    service.analyzer.comparar.return_value = json.dumps(payload)
    return service


def valid_payload(**changes):
    result = dict(compatibilidade=90, competencias_encontradas=["ICMS"],
                  competencias_faltantes=[], recomendacoes=[], explicacao="Evidências.", resumo="Resumo.")
    result.update(changes)
    return result


@pytest.mark.parametrize("payload", [[], "texto", 12, {},
    valid_payload(compatibilidade="alto"), valid_payload(compatibilidade=True),
    valid_payload(compatibilidade=float("nan")), valid_payload(compatibilidade=float("inf")),
    valid_payload(compatibilidade=101), valid_payload(competencias_encontradas="ICMS"),
    valid_payload(recomendacoes=[{}]), valid_payload(explicacao=3),
])
def test_invalid_ai_structure_falls_back_and_persists(payload):
    service = service_for(payload)
    result = service.comparar("ICMS, SAP e Python")
    assert result["id"] == 1
    assert result["compatibilidade"] is None
    assert "Python" in result["competencias_nao_informadas"]
    assert result["competencias_faltantes"] == []
    service.db.salvar_job_match.assert_called_once()


def test_unknown_is_not_gap_or_zero_and_defaults_to_investigate():
    result = service_for().comparar("ICMS e Python")
    assert result["compatibilidade"] is None
    assert result["recomendacao"] == "investigar"
    assert result["proximo_passo"]
    assert result["competencias_faltantes"] == []


def test_ai_cannot_claim_unproven_competence_or_confirm_a_gap():
    result = service_for(valid_payload(
        competencias_encontradas=["ICMS", "Python"], competencias_faltantes=["Excel"]
    )).comparar("ICMS, Python e Excel")
    assert result["competencias_encontradas"] == ["ICMS"]
    assert set(result["competencias_nao_informadas"]) == {"Python", "Excel"}
    assert result["competencias_faltantes"] == []


def test_explicit_negative_is_pending_not_confirmed_skill():
    result = service_for(text="Não tenho experiência em SAP.").comparar("SAP")
    assert result["competencias_encontradas"] == []
    assert result["compatibilidade"] is None


def test_confirmed_gap_requires_user_evidence():
    service = service_for()
    result = service.comparar("ICMS e Python", revisao={
        "lacunas_confirmadas": ["Python"], "evidencia": "Usuário confirmou em 27/09."
    })
    assert result["competencias_faltantes"] == ["Python"]
    assert result["compatibilidade"] == 50
    assert result["recomendacao"] == "investigar"


@pytest.mark.parametrize("state,evidence,expected", [
    ("alinhadas", "Escopo, requisitos essenciais e condições confirmados pelo usuário.", "priorizar"),
    ("incompativeis", "Presencial obrigatório em cidade incompatível com disponibilidade confirmada.", "descartar"),
    ("alinhadas", "", "investigar"), ("incompativeis", "", "investigar"),
])
def test_decision_requires_explicit_review(state, evidence, expected):
    result = service_for().comparar("ICMS", revisao={"condicoes": state, "evidencia": evidence})
    assert result["recomendacao"] == expected
    assert result["justificativa"] and result["proximo_passo"]


def test_recommendations_do_not_increase_document_score():
    profile = dict(cargo="Analista Fiscal", hard_skills=["ICMS"], recomendacoes=[])
    assert calculate(profile) == calculate({**profile, "recomendacoes": ["Melhore"] * 20})


def test_chat_uses_recent_history_in_chronological_order_and_objective():
    service = CareerAssistantService.__new__(CareerAssistantService)
    service.db = Mock()
    service.db.obter_analise_ativa.return_value = {"resume_id": 1, "cargo": "Fiscal", "area": "Fiscal"}
    service.db.obter_curriculo.return_value = {"texto": "Apuração de ICMS."}
    service.db.listar_confirmacoes_competencias.return_value = {}
    service.db.obter_objetivo_carreira.return_value = "Evoluir para Especialista"
    service.db.listar_mensagens_assistente.return_value = [
        {"role": "assistant", "content": "Resposta anterior"},
        {"role": "user", "content": "Pergunta anterior"},
    ]
    service.llm = Mock()
    service.llm.perguntar.return_value = "Próximos passos."
    service.conversar("E agora?")
    prompt = service.llm.perguntar.call_args.args[0]
    assert prompt.index("Pergunta anterior") < prompt.index("Resposta anterior")
    assert "Evoluir para Especialista" in prompt
    service.db.listar_mensagens_assistente.assert_called_once_with(limite=10, resume_id=1)


@pytest.mark.parametrize("answer", ["Sem nota", "NOTA: 120\nÓtimo", "NOTA: 70", "NOTA: 4.5\nTexto"])
def test_invalid_interview_feedback_does_not_invent_score(answer):
    service = CareerAssistantService.__new__(CareerAssistantService)
    service.db = Mock()
    service.db.obter_analise_ativa.return_value = {"resume_id": 1}
    service.llm = Mock()
    service.llm.perguntar.return_value = answer
    result = service.avaliar_resposta("Pergunta", "Resposta", "RH")
    assert result["nota"] is None
    assert service.db.salvar_entrevista.call_args.args[3] is None


def memory_db():
    db = Database.__new__(Database)
    db.conn = sqlite3.connect(":memory:")
    db.conn.row_factory = sqlite3.Row
    db.criar_tabelas()
    return db


def test_pending_match_roundtrip_and_objective_persistence():
    db = memory_db()
    try:
        columns = [row[1] for row in db.conn.execute("PRAGMA table_info(resumes)")]
        assert "id" in columns
        db.conn.execute("INSERT INTO resumes(nome_arquivo, caminho, texto) VALUES('cv', 'cv.txt', 'ICMS')")
        result = service_for().comparar("ICMS e Python")
        match_id = db.salvar_job_match(1, "ICMS e Python", result)
        saved = db.obter_job_match(match_id)
        restored = json.loads(saved["resultado_json"])
        assert restored["compatibilidade"] is None
        assert db.dashboard_job_match_metricas()["media"] is None
        assert restored["recomendacao"] == "investigar"
        assert restored["competencias_nao_informadas"] == ["Python"]
        db.salvar_objetivo_carreira("Especialista", 1)
        assert db.obter_objetivo_carreira(1) == "Especialista"
        db.criar_tabelas()  # migration remains idempotent
        assert db.obter_job_match(match_id) is not None
    finally:
        db.close()


def test_reports_keep_pending_result_and_recommendation(tmp_path):
    from docx import Document
    from pypdf import PdfReader

    from app.services.report_service import ReportService

    result = service_for().comparar("ICMS e Python")
    report = ReportService.__new__(ReportService)
    report.output_dir = tmp_path
    document = Document(report.exportar_job_match_docx(result))
    text = "\n".join(p.text for p in document.paragraphs)
    assert "sem pontuação" in text
    assert "Investigar" in text
    assert "Python" in text
    pdf = tmp_path / "match.pdf"
    report.exportar_job_match_pdf(result, pdf)
    text = "\n".join(page.extract_text() for page in PdfReader(pdf).pages)
    assert "Investigar" in text and "Python" in text
    assert "None%" not in text and "-1%" not in text


def test_pending_score_and_review_reset_in_ui(monkeypatch):
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    from app.ui.pages.job_match_page import JobMatchPage

    application = QApplication.instance() or QApplication([])
    db = Mock()
    db.listar_job_matches.return_value = []
    monkeypatch.setattr("app.ui.pages.job_match_page.Database", lambda: db)
    monkeypatch.setattr(JobMatchPage, "carregar_curriculo_ativo", lambda self: None)
    page = JobMatchPage()
    try:
        page.condicoes_match.setCurrentIndex(1)
        page.evidencia_match.setText("Revisão da vaga anterior")
        page.txtVaga.setPlainText("Nova vaga")
        assert page.condicoes_match.currentData() == "pendentes"
        assert not page.evidencia_match.text()
        page.mostrar_resultado(service_for().comparar("ICMS e Python"))
        assert page.score.lblScore.text() == "—"
        assert "Investigar" in page.decisao.lblConteudo.text()
        assert "Python" in page.pendentes.lblConteudo.text()
        legacy = dict(id=9, created_at="2026-09-01", nome_arquivo="cv", descricao="ICMS",
                      compatibilidade=40, resultado_json="{}", competencias_encontradas='["ICMS"]',
                      competencias_faltantes='["Python"]', recomendacoes="[]", explicacao="Antiga", resumo="")
        db.listar_job_matches.return_value = [legacy]
        db.obter_job_match.return_value = legacy
        page.carregar_historico()
        page.abrir_historico(0, 0)
        assert page.score.lblScore.text() == "—"
        assert "nota original: 40%" in page.explicacao.lblConteudo.text()
        assert page.resultado_atual["competencias_faltantes"] == []
        application.processEvents()
    finally:
        page.close()

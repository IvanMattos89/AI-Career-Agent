import json
import sqlite3
from datetime import date
from unittest.mock import Mock

import pytest

from app.ai.ats_score import assess as completeness
from app.ai.seniority_engine import assess as seniority
from app.database.sqlite_db import Database
from app.services.career_assistant_service import CareerAssistantService
from app.services.evidence_service import evidence_for, inventory, matrix
from app.services.job_match_service import JobMatchService
from app.services.resume_adaptation_service import ResumeAdaptationService
from app.services.resume_structure_service import ResumeStructureService


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setattr('app.database.sqlite_db.DATA_DIR', tmp_path)
    monkeypatch.setattr('app.database.sqlite_db.DATABASE', tmp_path / 'test.db')
    monkeypatch.setattr('app.database.sqlite_db.RESUMES_DIR', tmp_path / 'resumes')
    instance = Database()
    yield instance
    instance.close()


def profile(db, name, text):
    ident = db.salvar_curriculo(name, '/not-managed/' + name, text)
    db.salvar_analise(ident, cargo='Analista', area='Fiscal', hard_skills='SAP; ICMS', tecnologias='SAP')
    return ident


def test_switching_profiles_isolates_chat_interviews_objectives_and_confirmations(db):
    a = profile(db, 'a.txt', 'Apuração de ICMS em SAP.')
    b = profile(db, 'b.txt', 'Uso de Excel.')
    db.salvar_mensagem_assistente('user', 'Segredo A', a)
    db.salvar_mensagem_assistente('user', 'Segredo B', b)
    db.salvar_entrevista('P', 'R', 'F', None, 'RH', a)
    db.salvar_entrevista('P', 'R', 'F', None, 'RH', b)
    db.salvar_objetivo_carreira('Objetivo A', a)
    db.salvar_objetivo_carreira('Objetivo B', b)
    db.registrar_confirmacao_competencia(a, 'SAP', 'lacuna', 'Usuário, 29/09')
    db.registrar_confirmacao_competencia(b, 'SAP', 'pendente', 'Usuário, 29/09')
    db.definir_curriculo_ativo(b)
    assert [row['content'] for row in db.listar_mensagens_assistente(resume_id=b)] == ['Segredo B']
    assert db.listar_mensagens_assistente() == []
    assert db.obter_objetivo_carreira(b) == 'Objetivo B'
    assert db.excluir_curriculo(a)
    for table in ('assistant_messages', 'interview_sessions', 'profile_preferences', 'competency_confirmations'):
        assert db.conn.execute(f'SELECT COUNT(*) FROM {table} WHERE resume_id=?', (a,)).fetchone()[0] == 0
        assert db.conn.execute(f'SELECT COUNT(*) FROM {table} WHERE resume_id=?', (b,)).fetchone()[0] == 1
    with pytest.raises(sqlite3.IntegrityError):
        db.salvar_mensagem_assistente('assistant', 'Resposta atrasada A', a)
    db.conn.rollback()


def test_in_flight_chat_keeps_original_profile_even_if_active_changes(db):
    a = profile(db, 'a.txt', 'Apuração de ICMS em SAP.')
    b = profile(db, 'b.txt', 'Uso de Excel.')
    db.salvar_mensagem_assistente('user', 'Histórico privado A', a)
    db.salvar_mensagem_assistente('user', 'Histórico privado B', b)
    db.salvar_objetivo_carreira('Objetivo A', a)
    service = CareerAssistantService.__new__(CareerAssistantService)
    service.db = db
    service.resume_id = a
    service.llm = Mock()
    def answer(prompt, **kwargs):
        assert 'Histórico privado A' in prompt and 'Histórico privado B' not in prompt
        assert 'Objetivo A' in prompt
        assert 'tipo_experiencia' in prompt
        db.definir_curriculo_ativo(b)
        return 'Resposta para A'
    service.llm.perguntar.side_effect = answer
    service.conversar('Pergunta para A')
    assert db.listar_mensagens_assistente(resume_id=a)[0]['content'] == 'Resposta para A'
    assert len(db.listar_mensagens_assistente(resume_id=b)) == 1


def test_deleted_resume_id_is_not_reused_for_delayed_responses(db):
    first = profile(db, 'a.txt', 'Apuração de ICMS.')
    db.excluir_curriculo(first)
    second = profile(db, 'b.txt', 'Uso de Excel.')
    assert second > first


def test_migration_quarantines_legacy_rows_and_does_not_guess_owner(tmp_path, monkeypatch):
    monkeypatch.setattr('app.database.sqlite_db.DATA_DIR', tmp_path)
    monkeypatch.setattr('app.database.sqlite_db.DATABASE', tmp_path / 'legacy.db')
    with monkeypatch.context() as m:
        m.setattr(Database, '_migracao_perfis_e_evidencias', staticmethod(lambda cursor: None))
        legacy = Database()
        ident = legacy.salvar_curriculo('old.txt', '/not-managed/old.txt', 'Apuração de ICMS.')
        legacy.conn.execute("DELETE FROM schema_migrations WHERE version=8")
        legacy.conn.execute("INSERT INTO assistant_messages(role, content) VALUES('user', 'Conversa antiga')")
        legacy.conn.execute("INSERT INTO interview_sessions(pergunta, resposta, feedback, nota, tema) VALUES('P', 'R', 'F', 70, 'RH')")
        legacy.conn.execute("INSERT INTO career_preferences(id, objetivo) VALUES(1, 'Objetivo antigo')")
        legacy.conn.commit()
        legacy.close()
    upgraded = Database()
    try:
        assert upgraded.listar_mensagens_assistente(resume_id=ident) == []
        assert upgraded.obter_objetivo_carreira(ident) == ''
        assert upgraded.conn.execute('SELECT resume_id FROM assistant_messages').fetchone()[0] is None
        upgraded.salvar_mensagem_assistente('user', 'Nova vinculada', ident)
        upgraded.excluir_historico_sem_perfil()
        assert len(upgraded.listar_mensagens_assistente(resume_id=ident)) == 1
        assert upgraded.conn.execute('SELECT COUNT(*) FROM interview_sessions').fetchone()[0] == 0
        upgraded.criar_tabelas()
    finally:
        upgraded.close()


@pytest.mark.parametrize('text,kind', [
    ('Sem experiência em SAP.', 'negativa'),
    ('Não possuo experiência em SAP.', 'negativa'),
    ('CURSOS\nAcademia SAP FI concluída.', 'curso'),
    ('FORMAÇÃO\nTreinamento: executei transações SAP em laboratório.', 'curso'),
    ('COMPETÊNCIAS\nSAP', 'mencao'),
    ('EXPERIÊNCIA PROFISSIONAL\nUtilizei SAP na apuração de ICMS.', 'experiencia'),
    ('EXPERIÊNCIA PROFISSIONAL\nUtilizei SAP.\nSem experiência em SAP.', 'conflito'),
])
def test_shared_evidence_classification(text, kind):
    record = evidence_for('SAP', ResumeStructureService.from_text(text))
    assert record['tipo_experiencia'] == kind
    assert record['experiencia_sustentada'] == (kind == 'experiencia')
    assert record['origem'] == 'curriculo' and record['trecho']
    assert record['confirmacao_usuario'] is None


@pytest.mark.parametrize('text', ['Sem experiência em SAP.', 'CURSOS\nAcademia SAP FI.', 'COMPETÊNCIAS\nSAP'])
def test_match_and_adaptation_share_evidence_and_do_not_promote_course_or_negative(db, text):
    ident = profile(db, 'cv.txt', text)
    job = JobMatchService.__new__(JobMatchService)
    job.db = db
    job.analyzer = Mock()
    job.analyzer.llm.disponivel.return_value = False
    result = job.comparar('Requisito obrigatório: SAP')
    adaptation = ResumeAdaptationService.__new__(ResumeAdaptationService)
    adaptation.db = db
    adapted = adaptation.preparar('Requisito obrigatório: SAP', 'Analista Fiscal')
    assert not result['competencias_encontradas']
    assert not adapted['competencias_alinhadas']
    left = result['matriz_evidencias'][0]
    right = adapted['matriz_evidencias'][0]
    assert left['tipo_experiencia'] == right['tipo_experiencia']
    assert left['trecho'] == right['trecho']
    assert 'Experiência relatada no currículo em SAP' not in adapted['resumo_direcionado']
    db.registrar_confirmacao_competencia(ident, 'SAP', 'lacuna', 'Usuário confirmou em 29/09')
    adapted = adaptation.preparar('SAP')
    assert adapted['matriz_evidencias'][0]['status'] == 'Lacuna confirmada'
    assert adapted['matriz_evidencias'][0]['confirmacao_usuario']['fonte']


def test_inventory_keeps_unknown_mandatory_desirable_and_conditions():
    scope = inventory('Requisitos obrigatórios:\nSAP\nZetaCompliance\nDesejável:\nExcel\nCondições:\nPresencial em Manaus')
    assert any(row['categoria'] == 'Obrigatório' and 'ZetaCompliance' in row['trecho'] for row in scope['trechos'])
    assert any(row['categoria'] == 'Desejável' and 'Excel' in row['trecho'] for row in scope['trechos'])
    assert any(row['categoria'] == 'Condição' and 'Manaus' in row['trecho'] for row in scope['trechos'])
    assert scope['trechos_parciais'] > 0


def test_unknown_requirements_prevent_full_score_and_priority_even_with_known_skills(db):
    profile(db, 'cv.txt', 'Utilizei SAP na apuração de ICMS.')
    job = JobMatchService.__new__(JobMatchService)
    job.db = db
    job.analyzer = Mock()
    job.analyzer.llm.disponivel.return_value = False
    result = job.comparar('Obrigatório: SAP e ZetaCompliance', revisao={'condicoes': 'alinhadas', 'evidencia': 'Usuário, hoje'})
    assert result['compatibilidade'] is None
    assert result['recomendacao'] == 'investigar'
    assert 'ZetaCompliance' in json.dumps(result['inventario_requisitos'])
    assert result['competencias_encontradas'] == ['SAP']


def test_requirement_priority_does_not_spill_from_desirable_to_next_mandatory():
    records, _ = matrix('Desejável: Excel. Obrigatório: SAP', ResumeStructureService.from_text('Utilizei Excel e SAP.'))
    assert {row['requisito']: row['prioridade'] for row in records} == {'Excel': 'Desejável', 'SAP': 'Obrigatório'}


def test_dated_work_experience_supports_seniority_with_responsibility_evidence():
    text = ('EXPERIÊNCIA PROFISSIONAL\nEmpresa A | 01/2015 - 12/2020\nEmpresa B | 01/2019 - 12/2024\n'
            'Atuei com autonomia técnica. Resolvi problemas complexos. Liderei melhorias entre áreas.\n'
            'FORMAÇÃO\nUniversidade | 01/2000 - 12/2014')
    result = seniority(text, today=date(2026, 9, 29))
    assert result['anos'] == 10
    assert result['nivel'] == 'Sênior'
    assert all(result['sinais'].values())
    assert len(result['evidencias_tempo']) == 2
    assert result['limitacoes']


def test_ten_years_and_training_alone_do_not_establish_seniority():
    assert seniority('Tenho 10 anos de experiência.')['nivel'] == 'Não identificado'
    assert seniority('CURSOS\nAutonomia técnica, problemas complexos, liderança e responsabilidade.')['nivel'] == 'Não identificado'
    assert seniority('FORMAÇÃO\n2010 - 2020 Universidade') ['anos'] == 0


def test_complete_beginner_can_reach_100_without_years_or_many_skills():
    beginner = ('Ana Silva\nana@example.com\nOBJETIVO\nBusco minha primeira oportunidade na área fiscal.\n'
                'FORMAÇÃO\nCiências Contábeis na Universidade X\nCOMPETÊNCIAS\nExcel')
    experienced = beginner.replace('primeira oportunidade', 'próxima oportunidade') + '\nEXPERIÊNCIA PROFISSIONAL\nEmpresa X 2010 - 2025: apuração fiscal.'
    assert completeness({'texto_curriculo': beginner})['pontuacao'] == 100
    assert completeness({'texto_curriculo': experienced})['pontuacao'] == 100
    assert completeness({'texto_curriculo': beginner, 'anos_experiencia': 40, 'hard_skills': ['SAP'] * 50})['pontuacao'] == 100
    assert completeness({'texto_curriculo': ''})['pontuacao'] == 0


def test_analysis_persists_auditable_estimates(db):
    from app.ai.analyzer import ResumeAnalyzer
    from app.ai.skill_detector import SkillDetector
    from app.services.analysis_service import AnalysisService
    text = 'EXPERIÊNCIA PROFISSIONAL\nEmpresa A 2015 - 2020\nApuração de ICMS.'
    ident = profile(db, 'cv.txt', text)
    analyzer = ResumeAnalyzer.__new__(ResumeAnalyzer)
    analyzer.skill_detector = SkillDetector()
    analyzer.llm = Mock()
    analyzer.llm.perguntar.side_effect = RuntimeError('offline')
    service = AnalysisService.__new__(AnalysisService)
    service.db = db
    service.analyzer = analyzer
    service.analisar_texto(ident, text)
    saved = json.loads(db.obter_analise(ident)['avaliacao_json'])
    assert saved['senioridade']['evidencias_tempo']
    assert saved['completude']['teto'] == 100
    assert saved['senioridade']['nivel'] == 'Não identificado'


def test_profile_switch_clears_visible_chat_interview_and_loads_its_objective(db, monkeypatch):
    import os
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    from PySide6.QtWidgets import QApplication

    from app.ui.pages.career_hub_page import CareerHubPage
    application = QApplication.instance() or QApplication([])
    a = profile(db, 'a.txt', 'Apuração de ICMS.')
    b = profile(db, 'b.txt', 'Uso de Excel.')
    db.salvar_mensagem_assistente('user', 'Conversa exclusiva A', a)
    db.salvar_mensagem_assistente('user', 'Conversa exclusiva B', b)
    db.salvar_objetivo_carreira('Objetivo A', a)
    db.salvar_objetivo_carreira('Objetivo B', b)
    db.definir_curriculo_ativo(a)
    monkeypatch.setattr('app.ui.pages.career_hub_page.Database', lambda: db)
    page = CareerHubPage()
    try:
        assert 'Conversa exclusiva A' in page.chat.toPlainText()
        page.mostrar_pergunta('Pergunta específica A')
        page.resposta.setPlainText('Resposta A')
        db.definir_curriculo_ativo(b)
        page.atualizar_perfil()
        assert 'Conversa exclusiva A' not in page.chat.toPlainText()
        assert 'Conversa exclusiva B' in page.chat.toPlainText()
        assert page.pergunta_atual == '' and page.resposta.toPlainText() == ''
        assert page.objetivo_carreira.text() == 'Objetivo B'
        page.objetivo_carreira.setText('Objetivo B atualizado')
        page.objetivo_carreira.editingFinished.emit()
        assert db.obter_objetivo_carreira(a) == 'Objetivo A'
        assert db.obter_objetivo_carreira(b) == 'Objetivo B atualizado'
        application.processEvents()
    finally:
        page.close()


def test_structured_copy_cannot_override_negative_in_original_text(db):
    ident = profile(db, 'cv.txt', 'Sem experiência em SAP.')
    forged = ResumeStructureService.from_text('EXPERIÊNCIA PROFISSIONAL\nUtilizei SAP na apuração.')
    db.conn.execute('UPDATE resumes SET structured_json=? WHERE id=?', (json.dumps(forged), ident))
    db.conn.commit()
    service = ResumeAdaptationService.__new__(ResumeAdaptationService)
    service.db = db
    result = service.preparar('SAP')
    assert result['matriz_evidencias'][0]['tipo_experiencia'] == 'negativa'
    assert 'Utilizei SAP na apuração' not in result['texto_previa']
    assert not result['competencias_alinhadas']

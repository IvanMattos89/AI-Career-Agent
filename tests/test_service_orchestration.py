import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from app.services.analysis_service import AnalysisService
from app.services.application_studio_service import ApplicationStudioService
from app.services.dashboard_service import DashboardService
from app.services.history_service import HistoryService
from app.services.resume_structure_service import ResumeStructureService


class ServiceOrchestrationTest(unittest.TestCase):
    def test_analysis_service_persists_confidence_and_all_fields(self):
        analysis = SimpleNamespace(
            cargo="Analista Fiscal", area="Fiscal", senioridade="Sênior",
            confianca=0.91, ats_score=82, hard_skills=["ICMS"], soft_skills=[],
            tecnologias=["SAP"], idiomas=["Inglês"], certificacoes=["CRC"],
            anos_experiencia=10, nivel_curriculo="Avançado", palavras_chave=["ICMS"],
            pontos_fortes=["Compliance"], pontos_melhoria=[], competencias_faltantes=[],
            recomendacoes=["Quantificar resultados"], resumo="Resumo profissional completo.",
        )
        service = AnalysisService.__new__(AnalysisService)
        service.analyzer = Mock(analisar=Mock(return_value=analysis))
        service.db = Mock()

        result = service.analisar_texto(7, "currículo")

        self.assertIs(result, analysis)
        self.assertEqual(service.db.salvar_analise.call_args.kwargs["confianca"], 0.91)
        self.assertEqual(service.db.salvar_analise.call_args.kwargs["hard_skills"], "ICMS")

    def test_application_studio_offline_uses_only_resume_evidence(self):
        text = "Maria Silva\nEXPERIÊNCIA PROFISSIONAL\nAnalista Fiscal\n- Apuração de ICMS em SAP."
        structure = ResumeStructureService.from_text(text)
        db = Mock()
        db.obter_oportunidade.return_value = {
            "titulo": "Analista Fiscal", "empresa": "Empresa X",
            "descricao": "Requisitos: ICMS, SAP e inglês avançado.", "resume_id": 3,
        }
        db.obter_analise_ativa.return_value = {
            "resume_id": 3, "cargo": "Analista Fiscal", "area": "Fiscal",
            "senioridade": "Pleno", "hard_skills": "ICMS; SAP",
            "tecnologias": "SAP", "resumo": "Experiência fiscal.",
        }
        db.obter_curriculo.return_value = {
            "texto": text,
            "structured_json": __import__("json").dumps(structure),
        }
        db.salvar_pacote_candidatura.return_value = 11
        service = ApplicationStudioService.__new__(ApplicationStudioService)
        service.db = db
        service.llm = Mock(disponivel=Mock(return_value=False))

        package = service.gerar_pacote(5)

        self.assertEqual(package["id"], 11)
        self.assertIn("ICMS", package["palavras_chave"])
        self.assertNotIn("inglês avançado", package["palavras_chave"])
        matrix = {item["requisito"]: item["status"] for item in package["matriz_evidencias"]}
        self.assertEqual(matrix["inglês avançado"], "Não comprovado")

    def test_dashboard_service_combines_resume_match_and_pipeline_metrics(self):
        service = DashboardService.__new__(DashboardService)
        service.db = Mock()
        service.db.dashboard_ultima_analise.return_value = {
            "cargo": "Analista Fiscal", "created_at": "2026-08-01",
        }
        service.db.dashboard_media_ats.return_value = 81
        service.db.dashboard_total_curriculos.return_value = 2
        service.db.dashboard_job_match_metricas.return_value = {"total": 4, "media": 76}
        service.db.metricas_candidaturas.return_value = {
            "total": 3, "entrevistas": 33.3, "acompanhamentos": 1,
            "melhor_fonte": "Vagas.com",
        }

        metrics = service.indicadores()

        self.assertEqual(metrics["ats"], 81)
        self.assertEqual(metrics["job_matches"], 4)
        self.assertEqual(metrics["melhor_fonte"], "Vagas.com")

    def test_history_service_delegates_explicit_resume_operations(self):
        service = HistoryService.__new__(HistoryService)
        service.db = Mock()

        service.listar_curriculos()
        service.obter_curriculo(2)
        service.definir_curriculo_ativo(2)
        service.excluir_curriculo(2)

        service.db.listar_historico.assert_called_once_with()
        service.db.obter_curriculo.assert_called_once_with(2)
        service.db.definir_curriculo_ativo.assert_called_once_with(2)
        service.db.excluir_curriculo.assert_called_once_with(2)

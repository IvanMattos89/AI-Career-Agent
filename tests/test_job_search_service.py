import unittest
from unittest.mock import patch

from app.services.job_search_service import JobSearchService


class JobSearchRecommendationTest(unittest.TestCase):
    def test_location_filter_accepts_only_brazil_and_respects_state_city(self):
        elegivel = JobSearchService._localizacao_elegivel
        self.assertTrue(elegivel("São Paulo, SP, Brasil", "SP", "São Paulo"))
        self.assertTrue(elegivel("Remote - Brazil"))
        self.assertFalse(elegivel("Cologne, Germany"))
        self.assertFalse(elegivel("Rio de Janeiro, RJ, Brasil", "SP"))
        self.assertFalse(elegivel("São Paulo, SP, Brasil", "SP", "Campinas"))

    def test_location_filter_accepts_brazilian_city_and_state_format(self):
        self.assertTrue(JobSearchService._localizacao_elegivel("São Paulo / SP", "SP", "São Paulo"))
        self.assertTrue(JobSearchService._localizacao_elegivel("São Paulo - SP", "SP"))
        self.assertTrue(JobSearchService._localizacao_elegivel("São Paulo, SP", "SP"))
        self.assertTrue(JobSearchService._localizacao_elegivel("São Paulo"))

    def test_normalizes_english_and_portuguese_modalities(self):
        normalize = JobSearchService._modalidade_normalizada

        self.assertEqual(normalize("Remote"), "remoto")
        self.assertEqual(normalize("Hybrid"), "hibrido")
        self.assertEqual(normalize("On-site"), "presencial")

    @patch("app.services.job_search_service.Database.obter_analise_ativa")
    def test_recommends_brazilian_fiscal_titles(self, obter_analise):
        obter_analise.return_value = {
            "cargo": "Analista Fiscal",
            "hard_skills": "EFD; ERP; Excel; ICMS; IPI; ISS",
        }

        resultado = JobSearchService().recomendacao_para_curriculo()

        self.assertEqual(resultado["principal"], "Analista Fiscal")
        self.assertIn("Analista Tributário", resultado["titulos"])
        self.assertIn("SPED Fiscal", resultado["palavras_chave"])
        self.assertIn("ICMS", resultado["competencias_comprovadas"])
        self.assertIn("SPED Fiscal", resultado["palavras_sugeridas"])
        self.assertIn("Tax Compliance Analyst", resultado["consultas_fontes"])
        self.assertIn("tax accountant", resultado["consultas_fontes"])
        self.assertIn("accountant", resultado["consultas_fontes"])

    @patch("app.services.job_search_service.Database.obter_analise_ativa")
    def test_uses_broader_query_when_exact_query_returns_no_vacancies(self, obter_analise):
        obter_analise.return_value = {"cargo": "Analista Fiscal", "hard_skills": "ICMS; SPED"}
        service = JobSearchService()
        vaga = {"titulo": "Senior Accountant", "empresa": "Empresa", "descricao": "accountant", "url": "", "fonte": "Teste", "localizacao": "Remoto", "tags": []}
        def fake_search(query, *_args, **_kwargs):
            return [vaga] if query == "accountant" else []

        with patch.object(service, "buscar", side_effect=fake_search) as buscar:
            resultado = service.buscar_para_curriculo()

        self.assertEqual(resultado["consulta_utilizada"], "accountant")
        self.assertEqual(resultado["vagas"], [vaga])
        self.assertGreater(buscar.call_count, 3)

    @patch("app.services.job_search_service.Database.obter_analise_ativa")
    def test_combines_and_deduplicates_results_from_all_equivalent_queries(self, obter_analise):
        obter_analise.return_value = {"cargo": "Analista Fiscal", "hard_skills": "ICMS; SAP"}
        service = JobSearchService()
        fiscal = {
            "id": 1, "canonical_key": "empresa|fiscal|sp", "titulo": "Analista Fiscal",
            "empresa": "Empresa", "localizacao": "São Paulo / SP", "descricao": "ICMS",
            "rank_score": 70,
        }
        sap = {
            "id": 2, "canonical_key": "consultoria|sap|br", "titulo": "Consultor SAP Fiscal",
            "empresa": "Consultoria", "localizacao": "Brasil", "descricao": "SAP",
            "rank_score": 80,
        }

        def fake_search(query, *_args, **_kwargs):
            if query == "Analista Fiscal":
                return [fiscal]
            if query == "Consultor SAP Fiscal":
                return [fiscal, sap]
            return []

        with patch.object(service, "buscar", side_effect=fake_search):
            result = service.buscar_para_curriculo()

        self.assertEqual([job["id"] for job in result["vagas"]], [2, 1])
        self.assertIn("Analista Fiscal", result["consulta_utilizada"])
        self.assertIn("Consultor SAP Fiscal", result["consulta_utilizada"])

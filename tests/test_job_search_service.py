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

    @patch("app.services.job_search_service.Database.obter_ultima_analise")
    def test_recommends_brazilian_fiscal_titles(self, obter_analise):
        obter_analise.return_value = {
            "cargo": "Analista Fiscal",
            "hard_skills": "EFD; ERP; Excel; ICMS; IPI; ISS",
        }

        resultado = JobSearchService().recomendacao_para_curriculo()

        self.assertEqual(resultado["principal"], "Analista Fiscal")
        self.assertIn("Analista Tributário", resultado["titulos"])
        self.assertIn("SPED Fiscal", resultado["palavras_chave"])
        self.assertEqual(resultado["consultas_fontes"], ["tax accountant", "accountant"])

    @patch("app.services.job_search_service.Database.obter_ultima_analise")
    def test_uses_broader_query_when_exact_query_returns_no_vacancies(self, obter_analise):
        obter_analise.return_value = {"cargo": "Analista Fiscal", "hard_skills": "ICMS; SPED"}
        service = JobSearchService()
        vaga = {"titulo": "Senior Accountant", "empresa": "Empresa", "descricao": "accountant", "url": "", "fonte": "Teste", "localizacao": "Remoto", "tags": []}
        with patch.object(service, "buscar", side_effect=[[], [], [vaga]]) as buscar:
            resultado = service.buscar_para_curriculo()

        self.assertEqual(resultado["consulta_utilizada"], "accountant")
        self.assertEqual(resultado["vagas"], [vaga])
        self.assertEqual(buscar.call_count, 3)

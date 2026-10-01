import unittest
from unittest.mock import Mock, patch

import requests

from app.services.job_providers import AdzunaProvider, GupyProvider, JoobleProvider


def response(payload):
    result = Mock()
    result.json.return_value = payload
    result.raise_for_status.return_value = None
    return result


class StructuredJobProvidersTest(unittest.TestCase):
    @patch("app.services.job_providers.requests.get")
    def test_gupy_uses_official_token_and_normalizes_external_job(self, get):
        get.return_value = response({"data": [{
            "id": 10, "name": "Analista Fiscal Sênior", "status": "published",
            "companyName": "Empresa Brasil", "addressCity": "São Paulo",
            "addressState": "SP", "description": "ICMS e SPED", "publicUrl": "https://gupy/job/10",
        }]})

        jobs = GupyProvider("secret").search("Analista Fiscal")

        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].provider, "Gupy")
        self.assertEqual(jobs[0].location_state, "SP")
        self.assertEqual(jobs[0].location_country, "")
        self.assertEqual(get.call_args.kwargs["headers"]["Authorization"], "Bearer secret")

    @patch("app.services.job_providers.requests.get")
    def test_adzuna_queries_brazil_catalog(self, get):
        get.return_value = response({"results": [{
            "id": "a1", "title": "Indirect Tax Analyst",
            "company": {"display_name": "Consultoria"},
            "location": {"display_name": "São Paulo, Brasil"},
            "description": "Indirect taxes", "redirect_url": "https://adzuna/job/a1",
            "salary_min": 8000, "salary_max": 10000,
        }]})

        jobs = AdzunaProvider("id", "key").search("tax analyst")

        self.assertEqual(jobs[0].salary, "8000 – 10000")
        self.assertEqual(get.call_args.kwargs["params"]["where"], "Brasil")

    @patch("app.services.job_providers.requests.post")
    def test_jooble_posts_structured_brazil_search(self, post):
        post.return_value = response({"jobs": [{
            "id": 20, "title": "Especialista Fiscal", "company": "Empresa",
            "location": "Curitiba, PR, Brasil", "snippet": "Tributos indiretos",
            "link": "https://jooble/job/20", "type": "CLT",
        }]})

        jobs = JoobleProvider("secret").search("Especialista Fiscal")

        self.assertEqual(jobs[0].provider, "Jooble")
        self.assertEqual(post.call_args.kwargs["json"]["location"], "Brasil")
        self.assertNotIn("secret", post.call_args.kwargs["json"])

    @patch("app.services.job_providers.requests.post")
    def test_provider_error_does_not_expose_api_key(self, post):
        post.side_effect = requests.ConnectionError(
            "failed https://jooble.org/api/super-secret-key"
        )

        with self.assertRaises(ValueError) as context:
            JoobleProvider("super-secret-key").search("Analista Fiscal")

        self.assertNotIn("super-secret-key", str(context.exception))


if __name__ == "__main__":
    unittest.main()

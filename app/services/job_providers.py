"""Provedores públicos de vagas com uma interface comum e resultados normalizados."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod

import requests
from bs4 import BeautifulSoup

from app.models.job_listing import JobListing, normalize_text
from app.services.job_match_service import JobMatchService


class JobProvider(ABC):
    name = "Provider"

    @abstractmethod
    def search(self, query: str) -> list[JobListing]:
        """Consulta somente endpoints ou páginas públicas."""


class ProviderRequestError(ValueError):
    """Erro sanitizado que nunca inclui tokens ou chaves na mensagem."""


def safe_request(callable_, provider: str):
    try:
        response = callable_()
        response.raise_for_status()
        return response
    except requests.RequestException as error:
        status = getattr(getattr(error, "response", None), "status_code", None)
        suffix = f" (HTTP {status})" if status else ""
        raise ProviderRequestError(f"Falha ao consultar {provider}{suffix}.") from error


FISCAL_ALIASES = (
    "analista fiscal", "analista tributario", "especialista fiscal",
    "especialista em tributos indiretos", "analista de tributos indiretos",
    "tax analyst", "indirect tax analyst", "tax accountant", "tax technology analyst",
    "consultor sap fiscal", "sap tax consultant", "consultor synchro", "tax one",
)


def query_aliases(query: str) -> tuple[str, ...]:
    normalized = normalize_text(query)
    fiscal_signals = ("fiscal", "tribut", "tax", "accountant", "icms", "sped")
    if any(signal in normalized for signal in fiscal_signals):
        return FISCAL_ALIASES
    terms = tuple(part for part in normalized.split() if len(part) >= 3)
    return (normalized, *terms)


def matches_query(query: str, text: str) -> bool:
    normalized = normalize_text(text)
    return any(alias in normalized for alias in query_aliases(query))


class VagasComProvider(JobProvider):
    name = "Vagas.com"
    url = "https://www.vagas.com.br/vagas-de-{}"

    @staticmethod
    def _slug(query: str) -> str:
        from app.models.job_listing import normalize_text

        return "-".join(part for part in normalize_text(query).split() if part)

    def search(self, query: str) -> list[JobListing]:
        response = requests.get(
            self.url.format(self._slug(query)),
            timeout=20,
            headers={"User-Agent": "Mozilla/5.0 (compatible; AI-Career-Agent/3.2)"},
        )
        response.raise_for_status()
        page = BeautifulSoup(response.text, "html.parser")
        results = []
        for item in page.select("li.vaga"):
            link = item.select_one("a.link-detalhes-vaga")
            location = item.select_one(".vaga-local")
            if not link or not location:
                continue
            title = link.get("title") or link.get_text(" ", strip=True)
            company = item.select_one(".emprVaga")
            description = item.select_one(".detalhes")
            results.append(
                JobListing(
                    title=title.strip(),
                    company=company.get_text(" ", strip=True) if company else "Empresa não informada",
                    location=" ".join(location.get_text(" ", strip=True).split()),
                    url=requests.compat.urljoin("https://www.vagas.com.br", link.get("href", "")),
                    description=JobMatchService.limpar_descricao(
                        description.get_text(" ", strip=True) if description else ""
                    ),
                    provider=self.name,
                )
            )
        return results


class RemotiveProvider(JobProvider):
    name = "Remotive"
    url = "https://remotive.com/api/remote-jobs"

    def search(self, query: str) -> list[JobListing]:
        response = requests.get(self.url, params={"search": query, "limit": 100}, timeout=20)
        response.raise_for_status()
        return [
            JobListing(
                title=item.get("title") or "Vaga sem título",
                company=item.get("company_name") or "Empresa não informada",
                location=item.get("candidate_required_location") or "Remoto",
                url=item.get("url") or "",
                description=JobMatchService.limpar_descricao(item.get("description") or ""),
                provider=self.name,
                external_id=str(item.get("id") or ""),
                tags=item.get("tags") or [],
                modality="Remoto",
                published_at=item.get("publication_date") or "",
            )
            for item in response.json().get("jobs", [])
        ]


class ArbeitnowProvider(JobProvider):
    name = "Arbeitnow"
    url = "https://www.arbeitnow.com/api/job-board-api"

    def search(self, _query: str) -> list[JobListing]:
        response = requests.get(self.url, timeout=20)
        response.raise_for_status()
        return [
            JobListing(
                title=item.get("title") or "Vaga sem título",
                company=item.get("company_name") or "Empresa não informada",
                location="Remoto" if item.get("remote") else (item.get("location") or "Não informado"),
                url=item.get("url") or "",
                description=JobMatchService.limpar_descricao(item.get("description") or ""),
                provider=self.name,
                external_id=str(item.get("slug") or ""),
                tags=item.get("tags") or [],
                modality="Remoto" if item.get("remote") else "Presencial/Híbrido",
                published_at=str(item.get("created_at") or ""),
            )
            for item in response.json().get("data", [])
        ]


class GreenhouseProvider(JobProvider):
    """Consulta boards públicos configurados em JOB_GREENHOUSE_BOARDS."""

    name = "Greenhouse"
    url = "https://boards-api.greenhouse.io/v1/boards/{board}/jobs"

    def __init__(self, boards: list[str] | None = None):
        configured = os.getenv("JOB_GREENHOUSE_BOARDS", "")
        self.boards = boards if boards is not None else [x.strip() for x in configured.split(",") if x.strip()]

    def search(self, query: str) -> list[JobListing]:
        results = []
        for board in self.boards:
            response = requests.get(self.url.format(board=board), params={"content": "true"}, timeout=20)
            response.raise_for_status()
            for item in response.json().get("jobs", []):
                content = JobMatchService.limpar_descricao(item.get("content") or "")
                if not matches_query(query, f"{item.get('title', '')} {content}"):
                    continue
                location = (item.get("location") or {}).get("name") or "Não informado"
                results.append(
                    JobListing(
                        title=item.get("title") or "Vaga sem título",
                        company=board.replace("-", " ").title(),
                        location=location,
                        url=item.get("absolute_url") or "",
                        description=content,
                        provider=self.name,
                        external_id=str(item.get("id") or ""),
                        published_at=item.get("updated_at") or "",
                    )
                )
        return results


class LeverProvider(JobProvider):
    """Consulta sites públicos configurados em JOB_LEVER_SITES."""

    name = "Lever"
    url = "https://api.lever.co/v0/postings/{site}"

    def __init__(self, sites: list[str] | None = None):
        configured = os.getenv("JOB_LEVER_SITES", "")
        self.sites = sites if sites is not None else [x.strip() for x in configured.split(",") if x.strip()]

    def search(self, query: str) -> list[JobListing]:
        results = []
        for site in self.sites:
            response = requests.get(self.url.format(site=site), params={"mode": "json"}, timeout=20)
            response.raise_for_status()
            for item in response.json():
                description = JobMatchService.limpar_descricao(
                    " ".join((item.get("descriptionPlain") or "", item.get("additionalPlain") or ""))
                )
                if not matches_query(query, f"{item.get('text', '')} {description}"):
                    continue
                categories = item.get("categories") or {}
                results.append(
                    JobListing(
                        title=item.get("text") or "Vaga sem título",
                        company=site.replace("-", " ").title(),
                        location=categories.get("location") or "Não informado",
                        url=item.get("hostedUrl") or item.get("applyUrl") or "",
                        description=description,
                        provider=self.name,
                        external_id=item.get("id") or "",
                        employment_type=categories.get("commitment") or "Não informado",
                        modality=categories.get("workplaceType") or "Não informado",
                    )
                )
        return results


class GupyProvider(JobProvider):
    """API oficial autenticada da organização, limitada a vagas externas publicadas."""

    name = "Gupy"
    url = "https://api.gupy.io/api/v1/jobs"

    def __init__(self, token: str | None = None):
        self.token = (token if token is not None else os.getenv("GUPY_API_TOKEN", "")).strip()

    @staticmethod
    def _items(payload):
        if isinstance(payload, list):
            return payload
        return payload.get("data") or payload.get("results") or payload.get("items") or []

    def search(self, query: str) -> list[JobListing]:
        if not self.token:
            return []
        response = safe_request(
            lambda: requests.get(
                self.url,
                params={
                    "name": query, "status": "published", "publicationType": "external",
                    "fields": "all", "perPage": 100, "page": 1,
                },
                headers={"Authorization": f"Bearer {self.token}", "Accept": "application/json"},
                timeout=20,
            ),
            self.name,
        )
        results = []
        for item in self._items(response.json()):
            title = item.get("name") or item.get("roleName") or "Vaga sem título"
            description = JobMatchService.limpar_descricao(
                item.get("description") or item.get("jobDescription") or ""
            )
            if not matches_query(query, f"{title} {description}"):
                continue
            location = ", ".join(
                str(value).strip() for value in (
                    item.get("addressCity"), item.get("addressState"),
                    item.get("addressCountry") or "Brasil",
                ) if value
            ) or "Brasil"
            results.append(JobListing(
                title=title,
                company=item.get("companyName") or item.get("careerPageName") or "Empresa Gupy",
                location=location,
                url=item.get("jobUrl") or item.get("publicUrl") or item.get("careerPageUrl") or "",
                description=description,
                provider=self.name,
                external_id=str(item.get("id") or ""),
                employment_type=item.get("type") or "Não informado",
                modality=item.get("workplaceType") or item.get("workModel") or "Não informado",
                published_at=str(item.get("publishedAt") or item.get("updatedAt") or ""),
            ))
        return results


class AdzunaProvider(JobProvider):
    """API estruturada do Adzuna para o catálogo brasileiro."""

    name = "Adzuna"
    url = "https://api.adzuna.com/v1/api/jobs/br/search/1"

    def __init__(self, app_id: str | None = None, app_key: str | None = None):
        self.app_id = (app_id if app_id is not None else os.getenv("ADZUNA_APP_ID", "")).strip()
        self.app_key = (app_key if app_key is not None else os.getenv("ADZUNA_APP_KEY", "")).strip()

    def search(self, query: str) -> list[JobListing]:
        if not self.app_id or not self.app_key:
            return []
        response = safe_request(
            lambda: requests.get(
                self.url,
                params={
                    "app_id": self.app_id, "app_key": self.app_key, "what": query,
                    "where": "Brasil", "results_per_page": 50,
                    "content-type": "application/json",
                },
                headers={"Accept": "application/json"},
                timeout=20,
            ),
            self.name,
        )
        results = []
        for item in response.json().get("results", []):
            salary = ""
            if item.get("salary_min") or item.get("salary_max"):
                salary = f"{item.get('salary_min') or '?'} – {item.get('salary_max') or '?'}"
            results.append(JobListing(
                title=item.get("title") or "Vaga sem título",
                company=(item.get("company") or {}).get("display_name") or "Empresa não informada",
                location=(item.get("location") or {}).get("display_name") or "Brasil",
                url=item.get("redirect_url") or "",
                description=JobMatchService.limpar_descricao(item.get("description") or ""),
                provider=self.name,
                external_id=str(item.get("id") or ""),
                employment_type=item.get("contract_type") or "Não informado",
                salary=salary,
                published_at=item.get("created") or "",
            ))
        return results


class JoobleProvider(JobProvider):
    """Agregador oficial Jooble, habilitado somente com chave de API."""

    name = "Jooble"
    url = "https://jooble.org/api/{key}"

    def __init__(self, api_key: str | None = None):
        self.api_key = (api_key if api_key is not None else os.getenv("JOOBLE_API_KEY", "")).strip()

    def search(self, query: str) -> list[JobListing]:
        if not self.api_key:
            return []
        response = safe_request(
            lambda: requests.post(
                self.url.format(key=self.api_key),
                json={"keywords": query, "location": "Brasil", "page": 1, "ResultOnPage": 50},
                headers={"Content-Type": "application/json"},
                timeout=20,
            ),
            self.name,
        )
        return [
            JobListing(
                title=item.get("title") or "Vaga sem título",
                company=item.get("company") or "Empresa não informada",
                location=item.get("location") or "Brasil",
                url=item.get("link") or "",
                description=JobMatchService.limpar_descricao(item.get("snippet") or ""),
                provider=self.name,
                external_id=str(item.get("id") or ""),
                employment_type=item.get("type") or "Não informado",
                salary=item.get("salary") or "",
                published_at=item.get("updated") or "",
            )
            for item in response.json().get("jobs", [])
        ]


def default_providers() -> list[JobProvider]:
    providers: list[JobProvider] = [
        VagasComProvider(), RemotiveProvider(), GreenhouseProvider(), LeverProvider()
    ]
    if os.getenv("GUPY_API_TOKEN", "").strip():
        providers.append(GupyProvider())
    if os.getenv("ADZUNA_APP_ID", "").strip() and os.getenv("ADZUNA_APP_KEY", "").strip():
        providers.append(AdzunaProvider())
    if os.getenv("JOOBLE_API_KEY", "").strip():
        providers.append(JoobleProvider())
    if os.getenv("JOB_ENABLE_ARBEITNOW", "false").strip().casefold() in {"1", "true", "yes", "sim"}:
        providers.append(ArbeitnowProvider())
    return providers

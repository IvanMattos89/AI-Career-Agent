"""Provedores públicos de vagas com uma interface comum e resultados normalizados."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod

import requests
from bs4 import BeautifulSoup

from app.models.job_listing import JobListing
from app.services.job_match_service import JobMatchService


class JobProvider(ABC):
    name = "Provider"

    @abstractmethod
    def search(self, query: str) -> list[JobListing]:
        """Consulta somente endpoints ou páginas públicas."""


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
                if query.casefold() not in f"{item.get('title', '')} {content}".casefold():
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
                if query.casefold() not in f"{item.get('text', '')} {description}".casefold():
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


def default_providers() -> list[JobProvider]:
    return [VagasComProvider(), RemotiveProvider(), ArbeitnowProvider(), GreenhouseProvider(), LeverProvider()]

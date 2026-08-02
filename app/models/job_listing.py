"""Modelo normalizado usado por todos os provedores públicos de vagas."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def normalize_text(value: str | None) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", text).strip().casefold()


def normalize_url(value: str | None) -> str:
    if not value:
        return ""
    parts = urlsplit(value.strip())
    path = parts.path.rstrip("/")
    query = urlencode([
        (key, item) for key, item in parse_qsl(parts.query, keep_blank_values=False)
        if not key.casefold().startswith("utm_")
        and key.casefold() not in {"source", "ref", "referrer", "tracking"}
    ])
    return urlunsplit((parts.scheme.casefold(), parts.netloc.casefold(), path, query, ""))


def normalize_company(value: str | None) -> str:
    text = normalize_text(value)
    text = re.sub(r"\b(?:ltda|limitada|s/?a|sa|inc|llc|corp|corporation)\b", " ", text)
    return re.sub(r"\s+", " ", text).strip(" -.,")


def normalize_title(value: str | None) -> str:
    text = normalize_text(value)
    replacements = {
        r"\bsr\.?\b": "senior",
        r"\bsenior\b": "senior",
        r"\bjr\.?\b": "junior",
        r"\bpl\.?\b": "pleno",
    }
    for pattern, replacement in replacements.items():
        text = re.sub(pattern, replacement, text)
    return re.sub(r"\s+", " ", text).strip(" -.,")


def normalize_location(value: str | None) -> str:
    text = normalize_text(value)
    text = re.sub(r"\b(?:brasil|brazil)\b", " ", text)
    text = re.sub(r"\s*[/,|-]\s*", " ", text)
    return re.sub(r"\s+", " ", text).strip()


@dataclass(slots=True)
class JobListing:
    title: str
    company: str = "Empresa não informada"
    location: str = "Não informado"
    url: str = ""
    description: str = ""
    provider: str = "Manual"
    external_id: str = ""
    tags: list[str] = field(default_factory=list)
    modality: str = "Não informado"
    seniority: str = "Não informada"
    employment_type: str = "Não informado"
    salary: str = ""
    published_at: str = ""
    rank_score: int = 0
    rank_explanation: str = ""
    decision: str = "nova"
    id: int | None = None

    @property
    def canonical_key(self) -> str:
        normalized_url = normalize_url(self.url)
        signature = "|".join(
            (normalize_company(self.company), normalize_title(self.title), normalize_location(self.location))
        )
        company_known = normalize_text(self.company) not in {"", "empresa nao informada"}
        # A assinatura permite reconhecer a mesma publicação vinda de URLs e
        # provedores diferentes. A URL fica como fallback quando faltam dados.
        raw = signature if company_known and normalize_text(self.location) else normalized_url or signature
        return hashlib.sha256(raw.encode("utf-8", errors="ignore")).hexdigest()

    def as_dict(self) -> dict:
        data = asdict(self)
        data["canonical_key"] = self.canonical_key
        # Compatibilidade com as telas e serviços anteriores.
        data.update(
            titulo=self.title,
            empresa=self.company,
            localizacao=self.location,
            descricao=self.description,
            fonte=self.provider,
        )
        return data

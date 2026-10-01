"""Localização de escritório e elegibilidade remota, sem consultas de rede."""

import json
import re
from functools import lru_cache
from pathlib import Path

from app.models.job_listing import normalize_text

ESTADOS_BRASIL = {
        "AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas", "BA": "Bahia",
        "CE": "Ceará", "DF": "Distrito Federal", "ES": "Espírito Santo", "GO": "Goiás",
        "MA": "Maranhão", "MT": "Mato Grosso", "MS": "Mato Grosso do Sul", "MG": "Minas Gerais",
        "PA": "Pará", "PB": "Paraíba", "PR": "Paraná", "PE": "Pernambuco", "PI": "Piauí",
        "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte", "RS": "Rio Grande do Sul",
        "RO": "Rondônia", "RR": "Roraima", "SC": "Santa Catarina", "SP": "São Paulo",
        "SE": "Sergipe", "TO": "Tocantins",
    }

@lru_cache(maxsize=1)
def municipalities():
    data = json.loads((Path(__file__).parents[1] / "data" / "municipios_br.json").read_text(encoding="utf-8"))
    cities: dict[str, set[str]] = {}
    for name, state in data["municipios"]:
        cities.setdefault(normalize_text(name), set()).add(state)
    return cities


def modality(value):
    value = normalize_text(value)
    # A hybrid arrangement must not inherit nationwide remote eligibility.
    if any(term in value for term in ("hibrid", "hybrid", "presencial/remoto")):
        return "hibrido"
    if any(term in value for term in ("remoto", "remote", "home office")):
        return "remoto"
    if any(term in value for term in ("presencial", "on site", "on-site", "onsite")):
        return "presencial"
    return ""


def normalize_job_location(location, country="", state="", city="", work_mode="", remote_scope=""):
    text = normalize_text(location)
    country = normalize_text(country)
    text = re.sub(r"(?<=\w)-([a-z]{2})$", r", \1", text)
    parts = [part.strip() for part in re.split(r"\s*[,/|()—–]\s*|\s+-\s+", text) if part.strip()]
    brazil = country in {"br", "bra", "brazil", "brasil"} or any(p in {"br", "bra", "brasil", "brazil"} for p in parts)
    foreign = bool(country and country not in {"br", "bra", "brazil", "brasil"}) or any(
        p in {"us", "usa", "united states", "estados unidos", "uk", "united kingdom", "portugal", "germany", "alemanha", "argentina", "canada", "chile", "peru", "mexico", "spain", "espanha", "france", "franca"}
        for p in parts
    )
    cities = municipalities()
    candidate_city = normalize_text(city)
    if not candidate_city:
        candidate_city = next((part for part in parts if part in cities), "")
    state_names = {normalize_text(name): code for code, name in ESTADOS_BRASIL.items()}
    raw_state = normalize_text(state)
    state_code = raw_state.upper() if raw_state.upper() in ESTADOS_BRASIL else state_names.get(raw_state, "")
    if not state_code:
        for part in parts:
            if part.upper() in ESTADOS_BRASIL and (brazil or candidate_city or len(parts) == 1):
                state_code = part.upper()
                break
            if part in state_names:
                state_code = state_names[part]
                break
    inferred = False
    if candidate_city in cities:
        possible = cities[candidate_city]
        if not state_code and len(possible) == 1:
            state_code = next(iter(possible))
        inferred = not brazil
        brazil = brazil or not foreign
    brazil = brazil or bool(state_code and not foreign)
    mode = modality(work_mode) or modality(location)
    # National eligibility requires an explicit scope, not merely a remote office.
    national = mode == "remoto" and (
        normalize_text(remote_scope) in {"br", "brasil", "brazil", "worldwide"}
        or (brazil and not state_code and not candidate_city)
    )
    return {"country": "BR" if brazil and not foreign else country,
            "state": state_code, "city": candidate_city, "modality": mode,
            "remote_national": national and not foreign, "inferred_city": inferred}


def eligible(location, requested_state="", requested_city="", **metadata):
    parsed = normalize_job_location(location, **metadata)
    if parsed["country"] != "BR":
        return False
    if parsed["remote_national"]:
        return True
    if requested_state and parsed["state"] != requested_state.upper():
        return False
    if requested_city and parsed["city"] != normalize_text(requested_city):
        return False
    return True

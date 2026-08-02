import os
import re
import time
import unicodedata
from datetime import datetime, timezone

import requests

from app.database.sqlite_db import Database
from app.models.job_listing import JobListing, normalize_text
from app.services.job_providers import default_providers


class JobSearchService:
    """Consulta fontes públicas de vagas sem scraping e filtra por relevância local."""

    ESTADOS_BRASIL = {
        "AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas", "BA": "Bahia",
        "CE": "Ceará", "DF": "Distrito Federal", "ES": "Espírito Santo", "GO": "Goiás",
        "MA": "Maranhão", "MT": "Mato Grosso", "MS": "Mato Grosso do Sul", "MG": "Minas Gerais",
        "PA": "Pará", "PB": "Paraíba", "PR": "Paraná", "PE": "Pernambuco", "PI": "Piauí",
        "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte", "RS": "Rio Grande do Sul",
        "RO": "Rondônia", "RR": "Roraima", "SC": "Santa Catarina", "SP": "São Paulo",
        "SE": "Sergipe", "TO": "Tocantins",
    }

    def __init__(self, providers=None, db=None):
        self.providers = providers if providers is not None else default_providers()
        self.db = db or Database()

    # Títulos que aparecem com frequência em anúncios brasileiros.  Os termos
    # técnicos são combinados com as competências efetivamente extraídas do
    # currículo; não são usados para inventar experiência do candidato.
    PERFIS_BRASIL = {
        "fiscal": {
            "principal": "Analista Fiscal",
            "titulos": [
                "Analista Fiscal", "Analista Fiscal Sênior", "Analista Tributário",
                "Analista Tributário Sênior",
                "Especialista Fiscal", "Especialista em Tributos Indiretos",
                "Indirect Tax Analyst", "Tax Technology Analyst", "Consultor SAP Fiscal",
                "SAP Tax Consultant", "Consultor Synchro/Tax One",
            ],
            "palavras_mercado": [
                "apuração de tributos", "obrigações acessórias", "escrituração fiscal",
                "SPED Fiscal", "EFD ICMS/IPI", "EFD Contribuições", "ICMS", "IPI",
                "PIS", "COFINS", "ISS", "legislação tributária",
            ],
            # As fontes públicas atualmente integradas são internacionais; este
            # equivalente só é usado internamente para consultá-las. A segunda
            # consulta é mais ampla porque nem toda fonte classifica vagas
            # fiscais como "tax accountant".
            "consultas_fontes": ["tax accountant", "accountant"],
        },
        "financeiro": {
            "principal": "Analista Financeiro",
            "titulos": ["Analista Financeiro", "Analista de Planejamento Financeiro", "Analista FP&A"],
            "palavras_mercado": ["fluxo de caixa", "conciliação", "orçamento", "Excel", "ERP"],
            "consultas_fontes": ["financial analyst", "finance analyst"],
        },
        "dados": {
            "principal": "Analista de Dados",
            "titulos": ["Analista de Dados", "Analista BI", "Data Analyst"],
            "palavras_mercado": ["SQL", "Power BI", "Excel", "dashboards", "análise de dados"],
            "consultas_fontes": ["data analyst", "business intelligence"],
        },
        "desenvolvimento": {
            "principal": "Desenvolvedor de Software",
            "titulos": ["Desenvolvedor de Software", "Desenvolvedor Python", "Software Developer"],
            "palavras_mercado": ["Python", "APIs", "Git", "banco de dados", "testes"],
            "consultas_fontes": ["software developer", "developer"],
        },
    }

    @staticmethod
    def _termos(termo):
        return [item.lower() for item in re.findall(r"[\w+#.]{3,}", termo, flags=re.UNICODE)]

    @staticmethod
    def _normalizar(texto):
        texto = unicodedata.normalize("NFKD", str(texto or ""))
        return "".join(caractere for caractere in texto if not unicodedata.combining(caractere)).lower()

    @classmethod
    def _localizacao_elegivel(cls, localizacao, estado="", cidade=""):
        """Aceita somente vagas explicitamente localizadas no Brasil."""
        local = cls._normalizar(localizacao)
        estado_na_localizacao = any(
            re.search(rf"/\s*{sigla.lower()}\b", local)
            for sigla in cls.ESTADOS_BRASIL
        )
        if "brasil" not in local and "brazil" not in local and not estado_na_localizacao:
            return False
        if estado:
            nome_estado = cls._normalizar(cls.ESTADOS_BRASIL.get(estado, estado))
            # Aceita tanto a sigla quanto o nome por extenso na fonte.
            if nome_estado not in local and not re.search(rf"(?<![a-z]){re.escape(estado.lower())}(?![a-z])", local):
                return False
        if cidade and cls._normalizar(cidade) not in local:
            return False
        return True

    @staticmethod
    def _deduplicar(vagas):
        """Combina resultados equivalentes preservando o registro mais completo."""
        unique = {}
        for vaga in vagas:
            if isinstance(vaga, JobListing):
                item = vaga
            else:
                item = JobListing(
                    title=vaga.get("titulo") or vaga.get("title") or "Vaga sem título",
                    company=vaga.get("empresa") or vaga.get("company") or "Empresa não informada",
                    location=vaga.get("localizacao") or vaga.get("location") or "Não informado",
                    url=vaga.get("url") or "",
                    description=vaga.get("descricao") or vaga.get("description") or "",
                    provider=vaga.get("fonte") or vaga.get("provider") or "Manual",
                    external_id=str(vaga.get("external_id") or ""),
                    tags=vaga.get("tags") or [],
                    modality=vaga.get("modality") or "Não informado",
                    seniority=vaga.get("seniority") or "Não informada",
                    employment_type=vaga.get("employment_type") or "Não informado",
                    salary=vaga.get("salary") or "",
                    published_at=vaga.get("published_at") or "",
                )
            current = unique.get(item.canonical_key)
            if current is None or len(item.description) > len(current.description):
                unique[item.canonical_key] = item
        return list(unique.values())

    @classmethod
    def _ranking(cls, vaga, terms, estado="", cidade="", modalidade="", senioridade=""):
        title = normalize_text(vaga.title)
        content = normalize_text(" ".join((vaga.title, vaga.description, " ".join(vaga.tags))))
        matches = sum(term in content for term in terms)
        skills_score = min(40, matches * 8)
        title_score = 25 if any(term in title for term in terms) else 0
        location_score = 0
        score = skills_score + title_score
        if cidade and normalize_text(cidade) in normalize_text(vaga.location):
            location_score = 15
        elif estado and normalize_text(estado) in normalize_text(vaga.location):
            location_score = 10
        elif "brasil" in normalize_text(vaga.location) or "brazil" in normalize_text(vaga.location):
            location_score = 5
        modality_score = 7 if modalidade and normalize_text(modalidade) in normalize_text(vaga.modality) else 0
        seniority_score = 8 if senioridade and normalize_text(senioridade) in content else 0
        recency_score = cls._pontuacao_recencia(vaga.published_at)
        score += location_score + modality_score + seniority_score + recency_score
        explanation = (
            f"Competências {skills_score}/40 • cargo {title_score}/25 • "
            f"localização {location_score}/15 • modalidade {modality_score}/7 • "
            f"senioridade {seniority_score}/8 • recência {recency_score}/5"
        )
        return min(100, score), explanation

    @staticmethod
    def _pontuacao_recencia(value):
        if not value:
            return 0
        try:
            published = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if published.tzinfo is None:
                published = published.replace(tzinfo=timezone.utc)
            days = (datetime.now(timezone.utc) - published).days
            return 5 if days <= 30 else (2 if days <= 90 else 0)
        except (TypeError, ValueError):
            return 0

    def buscar(
        self, termo, limite=25, estado="", cidade="", modalidade="", senioridade="",
        ranking_terms=None,
    ):
        termo = (termo or "").strip()
        if not termo:
            raise ValueError("Informe um cargo, área ou competência para buscar vagas.")
        filters = {
            "estado": estado, "cidade": cidade, "modalidade": modalidade,
            "senioridade": senioridade,
        }
        search_id = self.db.iniciar_busca_vagas(
            termo, filters, [provider.name for provider in self.providers]
        )
        candidates, errors = [], []
        for provider in self.providers:
            started = time.perf_counter()
            try:
                provider_results = provider.search(termo)
                candidates.extend(provider_results)
                eligible = sum(
                    self._localizacao_elegivel(item.location, estado, cidade)
                    for item in provider_results
                )
                self.db.registrar_metrica_provedor(
                    search_id, provider.name, len(provider_results), eligible,
                    round((time.perf_counter() - started) * 1000),
                )
            except (requests.RequestException, ValueError, KeyError, TypeError) as error:
                errors.append(f"{provider.name}: {error}")
                self.db.registrar_metrica_provedor(
                    search_id, provider.name, duration_ms=round((time.perf_counter() - started) * 1000),
                    error=str(error),
                )
        if not candidates:
            self.db.concluir_busca_vagas(search_id, 0)
            detail = "; ".join(errors) or "nenhum resultado publicado"
            raise RuntimeError("Nenhuma fonte de vagas respondeu: " + detail)

        terms = list(dict.fromkeys([*self._termos(termo), *(ranking_terms or [])]))
        terms = [normalize_text(item) for item in terms if normalize_text(item)]
        query_terms = self._termos(termo)
        minimum_terms = 2 if len(query_terms) > 1 else 1
        results = []
        for listing in self._deduplicar(candidates):
            if not self._localizacao_elegivel(listing.location, estado, cidade):
                continue
            if modalidade and normalize_text(modalidade) not in normalize_text(listing.modality):
                continue
            content = normalize_text(f"{listing.title} {' '.join(listing.tags)} {listing.description}")
            adherence = sum(normalize_text(item) in content for item in query_terms)
            if listing.description and adherence >= minimum_terms:
                listing.rank_score, listing.rank_explanation = self._ranking(
                    listing, terms, estado, cidade, modalidade, senioridade
                )
                results.append(listing)
        results.sort(key=lambda item: (item.rank_score, len(item.description)), reverse=True)
        output = []
        for position, listing in enumerate(results, start=1):
            item = listing.as_dict()
            listing_id, decision = self.db.salvar_vaga_encontrada(item, search_id, position)
            if decision == "descartada":
                continue
            item["id"] = listing_id
            item["decision"] = decision
            output.append(item)
            if len(output) >= limite:
                break
        self.db.concluir_busca_vagas(search_id, len(output))
        return output

    @staticmethod
    def _lista_habilidades(analise):
        return [item.strip() for item in (analise["hard_skills"] or "").split(";") if item.strip()]

    def recomendacao_para_curriculo(self):
        """Retorna títulos brasileiros e palavras-chave alinhados ao currículo ativo."""
        analise = self.db.obter_analise_ativa()
        if not analise:
            raise ValueError("Analise um currículo antes de buscar vagas recomendadas.")
        cargo = (analise["cargo"] or "").strip()
        habilidades = self._lista_habilidades(analise)
        contexto = " ".join([cargo, *habilidades]).lower()
        if any(item in contexto for item in ("fiscal", "tribut", "icms", "ipi", "sped", "efd")):
            perfil = self.PERFIS_BRASIL["fiscal"]
        elif any(item in contexto for item in ("financeir", "fp&a", "fpa")):
            perfil = self.PERFIS_BRASIL["financeiro"]
        elif any(item in contexto for item in ("dados", "data", "power bi", "sql")):
            perfil = self.PERFIS_BRASIL["dados"]
        elif any(item in contexto for item in ("desenvolv", "python", "software")):
            perfil = self.PERFIS_BRASIL["desenvolvimento"]
        elif cargo:
            perfil = {"principal": cargo, "titulos": [cargo], "palavras_mercado": [], "consultas_fontes": [cargo]}
        elif habilidades:
            perfil = {"principal": habilidades[0], "titulos": habilidades[:3], "palavras_mercado": [], "consultas_fontes": [" ".join(habilidades[:2])]}
        else:
            raise ValueError("Não foi possível identificar um cargo ou competência para a busca.")

        # Mantém primeiro as palavras que o currículo comprova e completa com
        # termos recorrentes do perfil, sem repetições e com leitura amigável.
        palavras = []
        for item in [*habilidades, *perfil["palavras_mercado"]]:
            if item.lower() not in {palavra.lower() for palavra in palavras}:
                palavras.append(item)
        custom_titles = [
            item.strip() for item in os.getenv("JOB_TARGET_TITLES", "").split(",") if item.strip()
        ]
        titles = list(dict.fromkeys([*custom_titles, *perfil["titulos"]]))
        source_queries = list(dict.fromkeys([*custom_titles, *perfil["consultas_fontes"]]))
        proven = habilidades[:12]
        suggested = [
            item for item in perfil["palavras_mercado"]
            if item.casefold() not in {skill.casefold() for skill in habilidades}
        ][:12]
        return {
            "principal": perfil["principal"],
            "titulos": titles,
            "palavras_chave": palavras[:12],
            "competencias_comprovadas": proven,
            "palavras_sugeridas": suggested,
            "consultas_fontes": source_queries,
        }

    def termo_para_curriculo(self):
        """Título brasileiro principal exibido e usado como recomendação na interface."""
        return self.recomendacao_para_curriculo()["principal"]

    def buscar_para_curriculo(
        self, limite=25, estado="", cidade="", modalidade="", senioridade=""
    ):
        recomendacao = self.recomendacao_para_curriculo()
        erros = []
        # Primeiro pesquisa pelo título brasileiro no feed nacional. Depois,
        # tenta equivalentes das fontes internacionais, sempre filtrados Brasil.
        consultas = [recomendacao["principal"], *recomendacao["consultas_fontes"]]
        for consulta in dict.fromkeys(consultas):
            try:
                vagas = self.buscar(
                    consulta, limite, estado, cidade, modalidade, senioridade,
                    ranking_terms=recomendacao["palavras_chave"],
                )
            except RuntimeError as erro:
                erros.append(str(erro))
                continue
            if vagas:
                return {
                    "termo": recomendacao["principal"], "recomendacao": recomendacao,
                    "consulta_utilizada": consulta, "vagas": vagas,
                }
        if erros:
            raise RuntimeError("Nenhuma fonte de vagas respondeu: " + "; ".join(erros))
        return {"termo": recomendacao["principal"], "recomendacao": recomendacao, "consulta_utilizada": None, "vagas": []}

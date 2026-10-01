import os
import re
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from app.database.sqlite_db import Database
from app.models.job_listing import JobListing, normalize_text
from app.services.job_location import ESTADOS_BRASIL, eligible, modality
from app.services.job_providers import default_providers


class JobSearchService:
    """Consulta fontes públicas de vagas sem scraping e filtra por relevância local."""

    ESTADOS_BRASIL = ESTADOS_BRASIL

    def __init__(self, providers=None, db=None):
        self.providers = providers if providers is not None else default_providers()
        self.db = db or Database()
        self._default_catalog = providers is None
        self.last_report = {}
        self._last_search_id = None

    # Títulos que aparecem com frequência em anúncios brasileiros.  Os termos
    # técnicos são combinados com as competências efetivamente extraídas do
    # currículo; não são usados para inventar experiência do candidato.
    PERFIS_BRASIL = {
        "fiscal": {
            "principal": "Analista Fiscal",
            "titulos": [
                "Analista Fiscal", "Analista Fiscal Sênior", "Analista Tributário",
                "Analista Tributário Sênior", "Analista de Tributos Indiretos",
                "Especialista Fiscal", "Especialista Tributário",
                "Especialista em Tributos Indiretos", "Indirect Tax Analyst",
                "Indirect Tax Specialist", "Tax Compliance Analyst",
                "Tax Technology Analyst", "Consultor SAP Fiscal", "SAP Tax Consultant",
                "Consultor Synchro", "Consultor Tax One",
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
            "consultas_fontes": [
                "Analista Fiscal", "Analista Tributário", "Especialista Fiscal",
                "Indirect Tax Analyst", "Tax Compliance Analyst", "Consultor SAP Fiscal",
                "tax accountant", "accountant",
            ],
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
        return eligible(localizacao, estado, cidade)

    @classmethod
    def _modalidade_normalizada(cls, value):
        return modality(value)

    @staticmethod
    def _listing_location_eligible(listing, estado="", cidade=""):
        return eligible(listing.location, estado, cidade, country=listing.location_country,
                        state=listing.location_state, city=listing.location_city,
                        work_mode=listing.modality, remote_scope=listing.remote_scope)

    @staticmethod
    def _deduplicar(vagas):
        """Combina resultados equivalentes preservando o registro mais completo."""
        unique: dict[str, JobListing] = {}
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
        elif estado and cls._localizacao_elegivel(vaga.location, estado):
            location_score = 10
        elif "brasil" in normalize_text(vaga.location) or "brazil" in normalize_text(vaga.location):
            location_score = 5
        modality_score = (
            7 if modalidade and cls._modalidade_normalizada(modalidade)
            == cls._modalidade_normalizada(vaga.modality) else 0
        )
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

    def _provider_report(self):
        active = list(dict.fromkeys(provider.name for provider in self.providers))
        names = ["Vagas.com", "Remotive", "Adzuna", "Jooble", "Greenhouse", "Lever", "Gupy", "Arbeitnow"] if self._default_catalog else []
        return {name: {"provider": name, "status": "aguardando" if name in active else "não configurada",
                       "consultas": 0, "falhas": 0, "recebidas": 0, "elegiveis": 0,
                       "exibidas": 0, "duplicadas": 0, "descartadas": 0, "limite": 0,
                       "filtros": {"localização": 0, "modalidade": 0, "relevância": 0, "cargo excluído": 0}}
                for name in dict.fromkeys([*names, *active])}

    @staticmethod
    def _diagnostic_status(report):
        if report["status"] == "não configurada":
            return
        if report["falhas"]:
            report["status"] = "falhou" if report["falhas"] == report["consultas"] else "falha parcial"
        elif not report["recebidas"]:
            report["status"] = "sem resultados"
        elif not report["elegiveis"]:
            report["status"] = "resultados eliminados por filtro"
        elif not report["exibidas"]:
            report["status"] = "resultados após filtros; fora da lista final"
        else:
            report["status"] = "resultados disponíveis"

    def _save_report(self, report):
        self.last_report = report
        if self._last_search_id is not None:
            self.db.salvar_diagnostico_busca(self._last_search_id, report)

    def buscar(
        self, termo, limite=25, estado="", cidade="", modalidade="", senioridade="",
        ranking_terms=None, incluir_modalidade_desconhecida=False,
    ):
        termo = (termo or "").strip()
        if not termo:
            raise ValueError("Informe um cargo, área ou competência para buscar vagas.")
        limite = max(1, min(200, int(limite)))
        filters = {"estado": estado, "cidade": cidade, "modalidade": modalidade,
                   "senioridade": senioridade, "incluir_modalidade_desconhecida": incluir_modalidade_desconhecida}
        search_id = self.db.iniciar_busca_vagas(termo, filters, [p.name for p in self.providers])
        self._last_search_id = search_id
        diagnostics = self._provider_report()
        candidates = []
        terms = list(dict.fromkeys([*self._termos(termo), *(ranking_terms or [])]))
        terms = [normalize_text(item) for item in terms if normalize_text(item)]
        query_terms = self._termos(termo)
        minimum_terms = 2 if len(query_terms) > 1 else 1
        rejected = [normalize_text(item) for item in os.getenv("JOB_REJECTED_TITLES", "").split(",") if item.strip()]
        started = {provider: time.perf_counter() for provider in self.providers}
        with ThreadPoolExecutor(max_workers=max(1, min(6, len(self.providers))), thread_name_prefix="job-provider") as pool:
            futures = {pool.submit(provider.search, termo): provider for provider in self.providers}
            for future in as_completed(futures):
                provider = futures[future]
                report = diagnostics[provider.name]
                report["consultas"] += 1
                try:
                    provider_results = future.result()
                    report["recebidas"] = len(provider_results)
                except Exception:
                    # Never persist raw exception URLs: they may contain credentials.
                    report["falhas"] += 1
                    self.db.registrar_metrica_provedor(search_id, provider.name,
                        duration_ms=round((time.perf_counter() - started[provider]) * 1000),
                        error="Falha na consulta; verifique conexão e configuração da fonte.")
                    continue
                eligible_brazil = 0
                for listing in provider_results:
                    listing.provider = provider.name
                    if not self._listing_location_eligible(listing, estado, cidade):
                        report["filtros"]["localização"] += 1
                        continue
                    eligible_brazil += 1
                    mode = modality(listing.modality) or modality(listing.location)
                    if modalidade and mode != modality(modalidade) and (mode or not incluir_modalidade_desconhecida):
                        report["filtros"]["modalidade"] += 1
                        continue
                    content = normalize_text(f"{listing.title} {' '.join(listing.tags)} {listing.description}")
                    if any(re.search(rf"(?<!\w){re.escape(item)}(?!\w)", normalize_text(listing.title)) for item in rejected):
                        report["filtros"]["cargo excluído"] += 1
                        continue
                    if not listing.description or sum(normalize_text(item) in content for item in query_terms) < minimum_terms:
                        report["filtros"]["relevância"] += 1
                        continue
                    report["elegiveis"] += 1
                    listing.rank_score, listing.rank_explanation = self._ranking(listing, terms, estado, cidade, modalidade, senioridade)
                    candidates.append(listing)
                self.db.registrar_metrica_provedor(search_id, provider.name, len(provider_results), eligible_brazil,
                    round((time.perf_counter() - started[provider]) * 1000))
        results = self._deduplicar(candidates)
        retained_ids = {id(item) for item in results}
        for listing in candidates:
            if id(listing) not in retained_ids:
                diagnostics[listing.provider]["duplicadas"] += 1
        results.sort(key=lambda item: (item.rank_score, len(item.description)), reverse=True)
        output: list[dict] = []
        for position, listing in enumerate(results, start=1):
            item = listing.as_dict()
            listing_id, decision = self.db.salvar_vaga_encontrada(item, search_id, position)
            report = diagnostics[listing.provider]
            if decision == "descartada":
                report["descartadas"] += 1
                continue
            if len(output) >= limite:
                report["limite"] += 1
                continue
            item.update(id=listing_id, decision=decision)
            output.append(item)
            report["exibidas"] += 1
        for report in diagnostics.values():
            self._diagnostic_status(report)
        self.db.concluir_busca_vagas(search_id, len(output))
        self._save_report({"consultas": [termo], "consultas_omitidas": [], "fontes": list(diagnostics.values()),
                           "exibidas": len(output), "limite_resultados": limite})
        active_reports = [r for r in diagnostics.values() if r["consultas"]]
        if not active_reports or all(r["falhas"] == r["consultas"] for r in active_reports):
            raise RuntimeError("Todas as fontes habilitadas falharam ou nenhuma está configurada. Consulte o diagnóstico por fonte.")
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
        palavras: list[str] = []
        for item in [*habilidades, *perfil["palavras_mercado"]]:
            if item.lower() not in {palavra.lower() for palavra in palavras}:
                palavras.append(item)
        custom_titles = [
            item.strip() for item in os.getenv("JOB_TARGET_TITLES", "").split(",") if item.strip()
        ]
        acceptable = [item.strip() for item in os.getenv("JOB_ACCEPTABLE_TITLES", "").split(",") if item.strip()]
        custom_titles = list(dict.fromkeys([*custom_titles, *acceptable]))
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
        self, limite=25, estado="", cidade="", modalidade="", senioridade="",
        incluir_modalidade_desconhecida=False, max_consultas=None,
    ):
        recomendacao = self.recomendacao_para_curriculo()
        limite = max(1, min(200, int(limite)))
        errors, all_jobs, used_queries = [], [], []
        available = []
        seen = set()
        for item in [*recomendacao["consultas_fontes"], recomendacao["principal"]]:
            key = normalize_text(item)
            if key and key not in seen:
                available.append(item)
                seen.add(key)
        try:
            query_limit = max(1, min(50, int(max_consultas if max_consultas is not None else os.getenv("JOB_SEARCH_MAX_QUERIES", "20"))))
        except (TypeError, ValueError):
            query_limit = 20
        consultas, omitted = available[:query_limit], available[query_limit:]
        reports = []
        for consulta in dict.fromkeys(consultas):
            try:
                vagas = self.buscar(
                    consulta, limite, estado, cidade, modalidade, senioridade,
                    ranking_terms=recomendacao["palavras_chave"],
                    incluir_modalidade_desconhecida=incluir_modalidade_desconhecida,
                )
            except RuntimeError as erro:
                errors.append(str(erro))
                vagas = []
            if self.last_report:
                reports.append(self.last_report)
            if vagas:
                used_queries.append(consulta)
                all_jobs.extend(vagas)
        unique: dict[str, dict] = {}
        for job in all_jobs:
            key = (
                job.get("canonical_key") or job.get("url") or job.get("id")
                or "|".join(normalize_text(job.get(field, "")) for field in (
                    "titulo", "empresa", "localizacao",
                ))
            )
            current = unique.get(key)
            if current is None or job.get("rank_score", 0) > current.get("rank_score", 0):
                unique[key] = job
        jobs = sorted(
            unique.values(), key=lambda item: (item.get("rank_score", 0), len(item.get("descricao", ""))),
            reverse=True,
        )[:limite]
        if reports:
            combined = self._provider_report()
            for query_report in reports:
                for source in query_report["fontes"]:
                    target = combined[source["provider"]]
                    for key in ("consultas", "falhas", "recebidas", "elegiveis", "duplicadas", "descartadas", "limite"):
                        target[key] += source[key]
                    for key, count in source["filtros"].items():
                        target["filtros"][key] += count
            unique_objects = {id(job) for job in unique.values()}
            displayed_objects = {id(job) for job in jobs}
            for job in all_jobs:
                provider = job.get("provider") or job.get("fonte")
                if provider in combined and id(job) not in unique_objects:
                    combined[provider]["duplicadas"] += 1
            for job in unique.values():
                provider = job.get("provider") or job.get("fonte")
                if provider in combined and id(job) not in displayed_objects:
                    combined[provider]["limite"] += 1
            for job in jobs:
                provider = job.get("provider") or job.get("fonte")
                if provider in combined:
                    combined[provider]["exibidas"] += 1
            for report in combined.values():
                self._diagnostic_status(report)
            self._save_report({"consultas": consultas, "consultas_omitidas": omitted,
                               "fontes": list(combined.values()), "exibidas": len(jobs),
                               "limite_resultados": limite,
                               "nota": "Contagens somam consultas e podem repetir vagas; exibidas são únicas após ranking e limite."})
        if not jobs and errors and len(errors) == len(consultas):
            raise RuntimeError("As buscas personalizadas falharam. Consulte o diagnóstico por fonte.")
        return {
            "termo": recomendacao["principal"], "recomendacao": recomendacao,
            "consulta_utilizada": ", ".join(used_queries) or None, "vagas": jobs,
            "consultas_executadas": consultas, "consultas_omitidas": omitted,
        }

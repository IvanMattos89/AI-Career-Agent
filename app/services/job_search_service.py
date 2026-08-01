import re
import unicodedata

import requests
from bs4 import BeautifulSoup

from app.database.sqlite_db import Database
from app.models.job_listing import JobListing, normalize_text
from app.services.job_match_service import JobMatchService
from app.services.job_providers import default_providers


class JobSearchService:
    """Consulta fontes públicas de vagas sem scraping e filtra por relevância local."""

    REMOTIVE_URL = "https://remotive.com/api/remote-jobs"
    ARBEITNOW_URL = "https://www.arbeitnow.com/api/job-board-api"
    VAGAS_URL = "https://www.vagas.com.br/vagas-de-{}"
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
                "Analista Fiscal", "Analista Fiscal Pleno", "Analista Tributário",
                "Analista Fiscal e Tributário", "Analista de Impostos",
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

    @classmethod
    def _slug_busca(cls, termo):
        normalizado = cls._normalizar(termo)
        palavras = re.findall(r"[a-z0-9]+", normalizado)
        return "-".join(palavras)

    def _vagas_com(self, termo):
        """Lê a listagem pública brasileira, sem acessar área autenticada."""
        slug = self._slug_busca(termo)
        resposta = requests.get(
            self.VAGAS_URL.format(slug), timeout=20,
            headers={"User-Agent": "Mozilla/5.0 (compatible; AI-Career-Agent/3.1)"},
        )
        resposta.raise_for_status()
        pagina = BeautifulSoup(resposta.text, "html.parser")
        vagas = []
        for item in pagina.select("li.vaga"):
            link = item.select_one("a.link-detalhes-vaga")
            if not link:
                continue
            titulo = link.get("title") or link.get_text(" ", strip=True)
            empresa = item.select_one(".emprVaga")
            localizacao = item.select_one(".vaga-local")
            descricao = item.select_one(".detalhes")
            if not titulo or not localizacao:
                continue
            vagas.append({
                "titulo": titulo.strip(),
                "empresa": empresa.get_text(" ", strip=True) if empresa else "Empresa não informada",
                "localizacao": " ".join(localizacao.get_text(" ", strip=True).split()),
                "url": requests.compat.urljoin("https://www.vagas.com.br", link.get("href", "")),
                "descricao": JobMatchService.limpar_descricao(descricao.get_text(" ", strip=True) if descricao else ""),
                "tags": [],
                "fonte": "Vagas.com",
            })
        return vagas

    def _remotive(self, termo):
        resposta = requests.get(self.REMOTIVE_URL, params={"search": termo, "limit": 100}, timeout=20)
        resposta.raise_for_status()
        vagas = []
        for vaga in resposta.json().get("jobs", []):
            vagas.append({
                "titulo": vaga.get("title", "Vaga sem título"),
                "empresa": vaga.get("company_name", "Empresa não informada"),
                "localizacao": vaga.get("candidate_required_location", "Remoto"),
                "url": vaga.get("url", ""),
                "descricao": JobMatchService.limpar_descricao(vaga.get("description", "")),
                "tags": vaga.get("tags", []) or [],
                "fonte": "Remotive",
            })
        return vagas

    def _arbeitnow(self):
        resposta = requests.get(self.ARBEITNOW_URL, timeout=20)
        resposta.raise_for_status()
        vagas = []
        for vaga in resposta.json().get("data", []):
            localizacao = "Remoto" if vaga.get("remote") else (vaga.get("location") or "Não informado")
            vagas.append({
                "titulo": vaga.get("title", "Vaga sem título"),
                "empresa": vaga.get("company_name", "Empresa não informada"),
                "localizacao": localizacao,
                "url": vaga.get("url", ""),
                "descricao": JobMatchService.limpar_descricao(vaga.get("description", "")),
                "tags": vaga.get("tags", []) or [],
                "fonte": "Arbeitnow",
            })
        return vagas

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
        score = min(45, matches * 9)
        if any(term in title for term in terms):
            score += 25
        if cidade and normalize_text(cidade) in normalize_text(vaga.location):
            score += 15
        elif estado and normalize_text(estado) in normalize_text(vaga.location):
            score += 10
        elif "brasil" in normalize_text(vaga.location) or "brazil" in normalize_text(vaga.location):
            score += 5
        if modalidade and normalize_text(modalidade) in normalize_text(vaga.modality):
            score += 8
        if senioridade and normalize_text(senioridade) in content:
            score += 7
        return min(100, score)

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
            try:
                candidates.extend(provider.search(termo))
            except (requests.RequestException, ValueError, KeyError) as error:
                errors.append(f"{provider.name}: {error}")
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
                listing.rank_score = self._ranking(
                    listing, terms, estado, cidade, modalidade, senioridade
                )
                results.append(listing)
        results.sort(key=lambda item: (item.rank_score, len(item.description)), reverse=True)
        output = []
        for position, listing in enumerate(results[:limite], start=1):
            item = listing.as_dict()
            listing_id, decision = self.db.salvar_vaga_encontrada(item, search_id, position)
            if decision == "descartada":
                continue
            item["id"] = listing_id
            item["decision"] = decision
            output.append(item)
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
        return {
            "principal": perfil["principal"],
            "titulos": perfil["titulos"],
            "palavras_chave": palavras[:12],
            "consultas_fontes": perfil["consultas_fontes"],
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

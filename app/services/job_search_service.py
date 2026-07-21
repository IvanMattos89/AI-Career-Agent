import re
import unicodedata

import requests
from bs4 import BeautifulSoup

from app.database.sqlite_db import Database
from app.services.job_match_service import JobMatchService


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

    def buscar(self, termo, limite=10, estado="", cidade=""):
        termo = (termo or "").strip()
        if not termo:
            raise ValueError("Informe um cargo, área ou competência para buscar vagas.")
        candidatas, erros = [], []
        for fonte in (lambda: self._vagas_com(termo), lambda: self._remotive(termo), self._arbeitnow):
            try:
                candidatas.extend(fonte())
            except requests.RequestException as erro:
                erros.append(str(erro))
        if not candidatas:
            raise RuntimeError("Nenhuma fonte de vagas respondeu: " + "; ".join(erros))

        termos = self._termos(termo)
        minimo_termos = 2 if len(termos) > 1 else 1
        vagas = []
        for vaga in candidatas:
            if not self._localizacao_elegivel(vaga["localizacao"], estado, cidade):
                continue
            texto = " ".join([vaga["titulo"], " ".join(vaga["tags"]), vaga["descricao"]]).lower()
            aderencia = sum(item in texto for item in termos)
            if vaga["descricao"] and aderencia >= minimo_termos:
                vaga["_aderencia_busca"] = aderencia
                vagas.append(vaga)
        vagas.sort(key=lambda vaga: vaga["_aderencia_busca"], reverse=True)
        for vaga in vagas:
            vaga.pop("_aderencia_busca", None)
        return vagas[:limite]

    @staticmethod
    def _lista_habilidades(analise):
        return [item.strip() for item in (analise["hard_skills"] or "").split(";") if item.strip()]

    def recomendacao_para_curriculo(self):
        """Retorna títulos brasileiros e palavras-chave alinhados ao currículo ativo."""
        analise = Database().obter_ultima_analise()
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

    def buscar_para_curriculo(self, limite=10, estado="", cidade=""):
        recomendacao = self.recomendacao_para_curriculo()
        erros = []
        # Primeiro pesquisa pelo título brasileiro no feed nacional. Depois,
        # tenta equivalentes das fontes internacionais, sempre filtrados Brasil.
        consultas = [recomendacao["principal"], *recomendacao["consultas_fontes"]]
        for consulta in dict.fromkeys(consultas):
            try:
                vagas = self.buscar(consulta, limite, estado, cidade)
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

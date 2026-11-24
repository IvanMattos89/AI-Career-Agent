"""Evidências de empresas, remuneração comparável e histórico de vagas."""
import csv
import math
import re
from datetime import date

from app.models.job_listing import normalize_company, normalize_text

FISCAL_QUERIES = ["Analista Fiscal Sênior", "Analista Tributário Sênior", "Especialista Tributário",
                  "Especialista Fiscal", "Senior Tax Analyst", "Indirect Tax Specialist"]


def migrate_opportunity_tracking(cursor):
    cursor.execute("""CREATE TABLE company_evidence(
        company_key TEXT PRIMARY KEY, company TEXT NOT NULL, status TEXT NOT NULL,
        source TEXT NOT NULL, checked_on TEXT NOT NULL, note TEXT NOT NULL)""")
    cursor.execute("""CREATE TABLE listing_checks(
        listing_id INTEGER PRIMARY KEY REFERENCES job_listings(id) ON DELETE CASCADE,
        status TEXT NOT NULL, source TEXT NOT NULL, checked_on TEXT NOT NULL, note TEXT NOT NULL)""")
    cursor.execute("""CREATE TABLE listing_observations(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        listing_id INTEGER NOT NULL REFERENCES job_listings(id) ON DELETE CASCADE,
        search_id INTEGER REFERENCES job_searches(id) ON DELETE CASCADE,
        observed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        event TEXT NOT NULL, copies INTEGER NOT NULL DEFAULT 1)""")
    cursor.execute("CREATE INDEX idx_observations_search ON listing_observations(search_id, listing_id)")


def salary_assessment(text, minimum=0, include_unknown=True):
    if isinstance(minimum, bool) or not isinstance(minimum, (int, float)) or not math.isfinite(minimum) or minimum < 0:
        raise ValueError("Informe remuneração mínima válida.")
    normalized = normalize_text(text)
    monthly = bool(re.search(r"/mes|mensal|por mes|ao mes", normalized))
    brl = "r$" in normalized or "brl" in normalized
    ambiguous = bool(re.search(r"anual|/ano|por ano|hora|usd|eur|bonus|variavel|\+", normalized))
    values = re.findall(r"\d{1,3}(?:\.\d{3})+(?:,\d{2})?|\d+(?:,\d{2})?", normalized)
    if not monthly or not brl or ambiguous or not 1 <= len(values) <= 2:
        return {"eligible": not minimum or include_unknown, "status": "A confirmar: moeda, período ou valor não comparável", "min": None, "max": None}
    amounts = [float(v.replace(".", "").replace(",", ".")) for v in values]
    if "mil" in normalized or "k" in normalized or min(amounts) <= 0:
        return {"eligible": not minimum or include_unknown, "status": "A confirmar: formato de remuneração", "min": None, "max": None}
    low = min(amounts)
    high: float | None = max(amounts)
    if re.search(r"a partir|desde|acima de", normalized) and len(amounts) == 1:
        high = None
    status = "Faixa mensal BRL divulgada"
    if minimum and low < minimum and (high is None or high >= minimum):
        status = "A confirmar: negociação dentro da faixa"
    return {"eligible": high is None or high >= minimum, "status": status, "min": low, "max": high}


class OpportunityTracking:
    def __init__(self, db):
        self.db = db

    @staticmethod
    def _evidence(source, checked_on, note):
        if not source.strip() or not note.strip():
            raise ValueError("Informe fonte e evidência da confirmação.")
        parsed = date.fromisoformat(checked_on)
        if parsed > date.today():
            raise ValueError("A data de verificação não pode estar no futuro.")

    def set_company(self, company, status, source, checked_on, note):
        if status not in {"confirmada", "nao", "pendente"} or not normalize_company(company):
            raise ValueError("Empresa ou classificação inválida.")
        if normalize_text(company) in {"empresa nao informada", "empresa gupy"}:
            raise ValueError("Identifique a empresa antes de classificá-la.")
        self._evidence(source, checked_on, note)
        with self.db.conn:
            self.db.conn.execute("""INSERT INTO company_evidence VALUES (?,?,?,?,?,?)
                ON CONFLICT(company_key) DO UPDATE SET company=excluded.company,
                status=excluded.status, source=excluded.source, checked_on=excluded.checked_on,
                note=excluded.note""", (normalize_company(company), company, status, source, checked_on, note))

    def company(self, company, description=""):
        row = self.db.conn.execute("SELECT * FROM company_evidence WHERE company_key=?", (normalize_company(company),)).fetchone()
        if row:
            result = dict(row)
            result["prioritize"] = row["status"] == "confirmada" and (date.today() - date.fromisoformat(row["checked_on"])).days <= 180
            result["label"] = "Multinacional confirmada em registro" if result["prioritize"] else (
                "Não multinacional em registro" if row["status"] == "nao" and (date.today() - date.fromisoformat(row["checked_on"])).days <= 180
                else "Classificação pendente ou antiga; revisar fonte e data")
            return result
        return {"prioritize": False, "status": "pendente", "source": "Anúncio" if "multinacional" in normalize_text(description) else "",
                "label": "Multinacional indicada no anúncio; confirmar" if "multinacional" in normalize_text(description) else "Porte internacional a confirmar"}

    def observe(self, listing_id, search_id, previously_known, copies=1):
        with self.db.conn:
            self.db.conn.execute("INSERT INTO listing_observations(listing_id,search_id,event,copies) VALUES (?,?,?,?)",
                                 (listing_id, search_id, "repetida" if previously_known else "nova", max(1, copies)))

    def set_availability(self, listing_id, status, source, checked_on, note):
        if status not in {"aberta", "encerrada", "pendente"}:
            raise ValueError("Estado de disponibilidade inválido.")
        self._evidence(source, checked_on, note)
        with self.db.conn:
            self.db.conn.execute("""INSERT INTO listing_checks VALUES (?,?,?,?,?)
                ON CONFLICT(listing_id) DO UPDATE SET status=excluded.status,source=excluded.source,
                checked_on=excluded.checked_on,note=excluded.note""", (listing_id, status, source, checked_on, note))

    def availability(self, listing_id):
        row = self.db.conn.execute("SELECT * FROM listing_checks WHERE listing_id=?", (listing_id,)).fetchone()
        if not row:
            return "pendente"
        if row["status"] == "aberta" and (date.today() - date.fromisoformat(row["checked_on"])).days > 30:
            return "pendente"
        return row["status"]

    def report(self, days=7):
        rows = self.db.conn.execute("""SELECT j.*, c.source AS availability_source,
            c.checked_on AS checked_on, c.note AS availability_note,
            COALESCE(SUM(CASE WHEN o.observed_at >= datetime('now', ?) AND o.event='nova' THEN 1 ELSE 0 END),0) AS new_count,
            COALESCE(SUM(CASE WHEN o.observed_at >= datetime('now', ?) THEN
                o.copies - 1 + CASE WHEN o.event='repetida' THEN 1 ELSE 0 END ELSE 0 END),0) AS duplicates
            FROM job_listings j LEFT JOIN listing_checks c ON c.listing_id=j.id
            LEFT JOIN listing_observations o ON o.listing_id=j.id
            GROUP BY j.id ORDER BY j.last_seen_at DESC, j.id DESC""", (f"-{int(days)} days", f"-{int(days)} days"))
        result = []
        for row in rows:
            item = dict(row)
            item["availability"] = self.availability(item["id"])
            item["company_evidence"] = self.company(item["company"], item["description"])
            result.append(item)
        return result

    def pipeline(self, resume_id):
        if resume_id is None:
            return {"oportunidades": 0, "candidaturas": 0, "entrevistas": 0}
        rows = list(self.db.conn.execute("SELECT status, applied_at FROM opportunities WHERE resume_id=?", (resume_id,)))
        applied = {"Candidatado", "Triagem", "Entrevista com RH", "Entrevista técnica", "Proposta"}
        return {"oportunidades": len(rows), "candidaturas": sum(bool(r["applied_at"]) or r["status"] in applied for r in rows),
                "entrevistas": sum(r["status"] in {"Entrevista com RH", "Entrevista técnica"} for r in rows)}

    def export(self, path, rows):
        fields = ["title", "company", "provider", "location", "salary", "url", "availability", "new_count", "duplicates", "availability_source", "checked_on", "company_classification", "company_source", "company_checked_on"]
        with open(path, "w", newline="", encoding="utf-8-sig") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields, delimiter=";")
            writer.writeheader()
            for row in rows:
                evidence = row.get("company_evidence", {})
                values = {key: row.get(key) if row.get(key) is not None else "" for key in fields}
                values.update(company_classification=evidence.get("label", "A confirmar"),
                              company_source=evidence.get("source", ""), company_checked_on=evidence.get("checked_on", ""))
                # Prevent formula execution when the report is opened in Excel.
                writer.writerow({key: "'" + str(value) if str(value).startswith(("=", "+", "-", "@")) else value for key, value in values.items()})

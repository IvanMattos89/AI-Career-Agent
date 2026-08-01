import hashlib
import json
import sqlite3
from pathlib import Path

from app.config import DATA_DIR, DATABASE, RESUMES_DIR


class Database:

    def __init__(self):
        self.data_dir = DATA_DIR
        self.data_dir.mkdir(exist_ok=True)
        self.conn = sqlite3.connect(DATABASE, timeout=15)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")

        self.criar_tabelas()

    def close(self):
        """Fecha a conexão SQLite de forma segura quando o serviço é descartado."""
        if getattr(self, "conn", None) is not None:
            self.conn.close()
            self.conn = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, _exc, _traceback):
        if exc_type is not None and self.conn is not None:
            self.conn.rollback()
        self.close()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    def criar_tabelas(self):

        cursor = self.conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS resumes(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            nome_arquivo TEXT NOT NULL,
            caminho TEXT NOT NULL,
            texto TEXT NOT NULL,

            data_importacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        for coluna, tipo in [("content_hash", "TEXT")]:
            try:
                cursor.execute(f"ALTER TABLE resumes ADD COLUMN {coluna} {tipo}")
            except sqlite3.OperationalError as erro:
                if "duplicate column" not in str(erro).lower():
                    raise
        # Preenche hashes de currículos importados antes desta melhoria para
        # que novas importações do mesmo arquivo não gerem duplicatas.
        for registro in cursor.execute("SELECT id, texto FROM resumes WHERE content_hash IS NULL OR content_hash = ''").fetchall():
            content_hash = hashlib.sha256(registro["texto"].encode("utf-8", errors="ignore")).hexdigest()
            cursor.execute("UPDATE resumes SET content_hash = ? WHERE id = ?", (content_hash, registro["id"]))

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS profile(

            id INTEGER PRIMARY KEY CHECK(id = 1),

            cargo TEXT,
            area TEXT,
            senioridade TEXT,

            hard_skills TEXT,
            soft_skills TEXT,
            tecnologias TEXT,
            idiomas TEXT,
            certificacoes TEXT,

            resumo TEXT
        )
        """)

        # Mantém a escolha explícita do currículo que alimenta os recursos de
        # análise, busca e candidatura. Assim, importar outro arquivo não faz
        # o usuário perder o contexto da vaga em andamento.
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS app_state(
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS resume_analysis(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            resume_id INTEGER NOT NULL,

            cargo TEXT,
            area TEXT,
            senioridade TEXT,

            ats_score INTEGER,

            hard_skills TEXT,
            soft_skills TEXT,
            tecnologias TEXT,
            idiomas TEXT,
            certificacoes TEXT,

            resumo TEXT,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY(resume_id)
                REFERENCES resumes(id)
                ON DELETE CASCADE
   )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            descricao TEXT NOT NULL,
            titulo TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS job_matches(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resume_id INTEGER NOT NULL,
            job_id INTEGER NOT NULL,
            compatibilidade INTEGER NOT NULL,
            competencias_encontradas TEXT NOT NULL DEFAULT '[]',
            competencias_faltantes TEXT NOT NULL DEFAULT '[]',
            recomendacoes TEXT NOT NULL DEFAULT '[]',
            explicacao TEXT,
            resumo TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(resume_id) REFERENCES resumes(id) ON DELETE CASCADE,
            FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS opportunities(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            empresa TEXT,
            plataforma TEXT NOT NULL DEFAULT 'Manual',
            url TEXT,
            descricao TEXT,
            status TEXT NOT NULL DEFAULT 'Salva',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        for coluna, tipo in (("source_key", "TEXT"), ("updated_at", "TIMESTAMP")):
            try:
                cursor.execute(f"ALTER TABLE opportunities ADD COLUMN {coluna} {tipo}")
            except sqlite3.OperationalError as erro:
                if "duplicate column" not in str(erro).lower():
                    raise
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_opportunities_source_key ON opportunities(source_key) WHERE source_key IS NOT NULL")
        # Instalações anteriores não possuíam a chave. Preenchemos o primeiro
        # registro de cada oportunidade sem apagar histórico duplicado já salvo.
        oportunidades_antigas = cursor.execute(
            "SELECT id, titulo, empresa, plataforma, url FROM opportunities WHERE source_key IS NULL OR source_key = ''"
        ).fetchall()
        for oportunidade in oportunidades_antigas:
            chave = self._chave_oportunidade(
                oportunidade["titulo"], oportunidade["empresa"], oportunidade["plataforma"], oportunidade["url"]
            )
            if not chave:
                continue
            try:
                cursor.execute("UPDATE opportunities SET source_key = ? WHERE id = ?", (chave, oportunidade["id"]))
            except sqlite3.IntegrityError:
                # Há um registro equivalente mais antigo; mantemos este item
                # histórico sem chave e passamos a impedir novas duplicações.
                pass

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS interview_sessions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pergunta TEXT NOT NULL,
            resposta TEXT,
            feedback TEXT,
            nota INTEGER,
            tema TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS assistant_messages(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS application_packages(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            opportunity_id INTEGER NOT NULL,
            carta TEXT NOT NULL,
            resumo_direcionado TEXT NOT NULL,
            palavras_chave TEXT NOT NULL DEFAULT '[]',
            checklist TEXT NOT NULL DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(opportunity_id) REFERENCES opportunities(id) ON DELETE CASCADE
        )
        """)
        # ==========================================
        # Migração automática da tabela resume_analysis
        # ==========================================

        novas_colunas = [
            ("anos_experiencia", "INTEGER"),
            ("nivel_curriculo", "TEXT"),
            ("palavras_chave", "TEXT"),
            ("pontos_fortes", "TEXT"),
            ("pontos_melhoria", "TEXT"),
            ("competencias_faltantes", "TEXT"),
            ("recomendacoes", "TEXT"),
        ]

        for coluna, tipo in novas_colunas:
            try:
                cursor.execute(
                    f"ALTER TABLE resume_analysis ADD COLUMN {coluna} {tipo}"
                )
            except sqlite3.OperationalError:
                pass

        self._aplicar_migracoes(cursor)

        self.conn.commit()

    def _aplicar_migracoes(self, cursor):
        """Aplica evoluções incrementais e registra cada versão executada."""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations(
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        aplicadas = {row[0] for row in cursor.execute("SELECT version FROM schema_migrations")}
        if 1 not in aplicadas:
            self._migracao_busca_e_pipeline(cursor)
            cursor.execute(
                "INSERT INTO schema_migrations(version, name) VALUES(1, ?)",
                ("busca_normalizada_e_pipeline",),
            )

    @staticmethod
    def _migracao_busca_e_pipeline(cursor):
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS job_searches(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                filters_json TEXT NOT NULL DEFAULT '{}',
                providers_json TEXT NOT NULL DEFAULT '[]',
                result_count INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS job_listings(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                external_id TEXT,
                title TEXT NOT NULL,
                company TEXT,
                location TEXT,
                modality TEXT,
                seniority TEXT,
                employment_type TEXT,
                salary TEXT,
                url TEXT,
                description TEXT,
                provider TEXT NOT NULL,
                canonical_key TEXT NOT NULL UNIQUE,
                decision TEXT NOT NULL DEFAULT 'nova',
                rank_score INTEGER NOT NULL DEFAULT 0,
                published_at TEXT,
                first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS job_search_results(
                search_id INTEGER NOT NULL,
                listing_id INTEGER NOT NULL,
                position INTEGER NOT NULL,
                rank_score INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY(search_id, listing_id),
                FOREIGN KEY(search_id) REFERENCES job_searches(id) ON DELETE CASCADE,
                FOREIGN KEY(listing_id) REFERENCES job_listings(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS application_history(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                opportunity_id INTEGER NOT NULL,
                status_from TEXT,
                status_to TEXT NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(opportunity_id) REFERENCES opportunities(id) ON DELETE CASCADE
            )
        """)
        existing = {row[1] for row in cursor.execute("PRAGMA table_info(opportunities)")}
        columns = {
            "listing_id": "INTEGER",
            "applied_at": "TEXT",
            "salary_range": "TEXT",
            "work_model": "TEXT",
            "employment_type": "TEXT",
            "recruiter_name": "TEXT",
            "recruiter_email": "TEXT",
            "recruiter_phone": "TEXT",
            "next_action": "TEXT",
            "next_action_at": "TEXT",
            "resume_id": "INTEGER",
            "job_match_id": "INTEGER",
            "notes": "TEXT",
        }
        for name, definition in columns.items():
            if name not in existing:
                cursor.execute(f"ALTER TABLE opportunities ADD COLUMN {name} {definition}")
        cursor.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_opportunities_listing "
            "ON opportunities(listing_id) WHERE listing_id IS NOT NULL"
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_job_listings_decision ON job_listings(decision)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_opportunities_status ON opportunities(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_opportunities_next_action ON opportunities(next_action_at)")

       
    # ==========================================================
    # CURRÍCULOS
    # ==========================================================

    def salvar_curriculo(self, nome, caminho, texto):

        content_hash = hashlib.sha256(texto.encode("utf-8", errors="ignore")).hexdigest()
        existente = self.conn.execute("SELECT id FROM resumes WHERE content_hash = ?", (content_hash,)).fetchone()
        if existente:
            self.definir_curriculo_ativo(existente["id"])
            return existente["id"]

        cursor = self.conn.cursor()

        cursor.execute("""
        INSERT INTO resumes
        (
            nome_arquivo,
            caminho,
            texto,
            content_hash
        )
        VALUES
        (
            ?, ?, ?, ?
        )
        """, (nome, caminho, texto, content_hash))

        self.conn.commit()
        resume_id = cursor.lastrowid
        self.definir_curriculo_ativo(resume_id)
        return resume_id

    def listar_curriculos(self):

        cursor = self.conn.cursor()

        cursor.execute("""
        SELECT
            id,
            nome_arquivo,
            data_importacao
        FROM resumes
        ORDER BY id DESC
        """)

        return cursor.fetchall()

    def listar_curriculos_completos(self):

        cursor = self.conn.cursor()

        cursor.execute("""
        SELECT
            id,
            nome_arquivo,
            caminho,
            texto,
            data_importacao
        FROM resumes
        ORDER BY id DESC
        """)

        return cursor.fetchall()

    def obter_curriculo(self, resume_id):

        cursor = self.conn.cursor()

        cursor.execute("""
        SELECT
            id,
            nome_arquivo,
            caminho,
            texto,
            data_importacao
        FROM resumes
        WHERE id = ?
        """, (resume_id,))

        return cursor.fetchone()

    def excluir_curriculo(self, resume_id):
        cursor = self.conn.cursor()
        registro = self.obter_curriculo(resume_id)
        if not registro:
            return False
        try:
            # Bancos criados antes da migration usavam FK sem CASCADE em
            # resume_analysis. A limpeza explícita mantém a exclusão segura
            # tanto para esses bancos quanto para instalações novas.
            cursor.execute("DELETE FROM job_matches WHERE resume_id = ?", (resume_id,))
            cursor.execute("DELETE FROM resume_analysis WHERE resume_id = ?", (resume_id,))
            cursor.execute("DELETE FROM resumes WHERE id = ?", (resume_id,))
            cursor.execute("DELETE FROM jobs WHERE id NOT IN (SELECT DISTINCT job_id FROM job_matches)")
            cursor.execute("DELETE FROM app_state WHERE key = 'active_resume_id' AND value = ?", (str(resume_id),))
        except sqlite3.Error:
            self.conn.rollback()
            raise

        cursor.execute("SELECT COUNT(*) FROM resumes")

        total = cursor.fetchone()[0]

        if total == 0:
            cursor.execute(
                "DELETE FROM sqlite_sequence WHERE name='resumes'"
            )
        elif self.obter_curriculo_ativo_id() is None:
            proximo = self.conn.execute("SELECT id FROM resumes ORDER BY data_importacao DESC, id DESC LIMIT 1").fetchone()
            if proximo:
                self.definir_curriculo_ativo(proximo["id"])

        self.conn.commit()
        self._remover_arquivo_curriculo(registro["caminho"])
        return True

    @staticmethod
    def _remover_arquivo_curriculo(caminho):
        """Apaga somente cópias gerenciadas pelo aplicativo, nunca o original."""
        try:
            arquivo = Path(caminho).resolve()
            pasta = RESUMES_DIR.resolve()
            if arquivo.is_relative_to(pasta) and arquivo.is_file():
                arquivo.unlink()
        except OSError:
            # O banco já foi atualizado; um arquivo bloqueado pode ser apagado
            # em uma nova tentativa sem comprometer a integridade dos dados.
            pass

    def definir_curriculo_ativo(self, resume_id):
        if not self.conn.execute("SELECT 1 FROM resumes WHERE id = ?", (resume_id,)).fetchone():
            raise ValueError("Currículo não encontrado para ativação.")
        self.conn.execute(
            "INSERT INTO app_state(key, value) VALUES('active_resume_id', ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (str(resume_id),),
        )
        self.conn.commit()

    def obter_curriculo_ativo_id(self):
        estado = self.conn.execute("SELECT value FROM app_state WHERE key = 'active_resume_id'").fetchone()
        if not estado:
            return None
        try:
            return int(estado["value"])
        except (TypeError, ValueError):
            return None

    # ==========================================================
    # JOB MATCH
    # ==========================================================

    def obter_ultima_analise(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT a.*, r.nome_arquivo
            FROM resume_analysis a
            JOIN resumes r ON r.id = a.resume_id
            ORDER BY a.created_at DESC, a.id DESC
            LIMIT 1
        """)
        return cursor.fetchone()

    def obter_analise_ativa(self):
        """Obtém a análise do currículo escolhido; usa a mais recente no primeiro uso."""
        resume_id = self.obter_curriculo_ativo_id()
        if resume_id is None:
            registro = self.obter_ultima_analise()
            if registro:
                self.definir_curriculo_ativo(registro["resume_id"])
            return registro
        return self.conn.execute("""
            SELECT a.*, r.nome_arquivo
            FROM resume_analysis a JOIN resumes r ON r.id = a.resume_id
            WHERE a.resume_id = ?
            ORDER BY a.created_at DESC, a.id DESC LIMIT 1
        """, (resume_id,)).fetchone()

    def salvar_job_match(self, resume_id, descricao, resultado, titulo=None):
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO jobs (descricao, titulo) VALUES (?, ?)", (descricao, titulo))
        job_id = cursor.lastrowid
        cursor.execute("""
            INSERT INTO job_matches (
                resume_id, job_id, compatibilidade, competencias_encontradas,
                competencias_faltantes, recomendacoes, explicacao, resumo
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            resume_id, job_id, int(resultado.get("compatibilidade", 0)),
            json.dumps(resultado.get("competencias_encontradas", []), ensure_ascii=False),
            json.dumps(resultado.get("competencias_faltantes", []), ensure_ascii=False),
            json.dumps(resultado.get("recomendacoes", []), ensure_ascii=False),
            resultado.get("explicacao", ""), resultado.get("resumo", ""),
        ))
        self.conn.commit()
        return cursor.lastrowid

    def listar_job_matches(self, limite=20):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT jm.*, j.titulo, j.descricao, r.nome_arquivo
            FROM job_matches jm
            JOIN jobs j ON j.id = jm.job_id
            JOIN resumes r ON r.id = jm.resume_id
            ORDER BY jm.created_at DESC, jm.id DESC LIMIT ?
        """, (limite,))
        return cursor.fetchall()

    def obter_job_match(self, match_id):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT jm.*, j.titulo, j.descricao, r.nome_arquivo
            FROM job_matches jm JOIN jobs j ON j.id = jm.job_id
            JOIN resumes r ON r.id = jm.resume_id WHERE jm.id = ?
        """, (match_id,))
        return cursor.fetchone()

    # ==========================================================
    # V3.2: buscas e vagas encontradas
    # ==========================================================

    def iniciar_busca_vagas(self, query, filters=None, providers=None):
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO job_searches(query, filters_json, providers_json) VALUES (?, ?, ?)",
            (
                query,
                json.dumps(filters or {}, ensure_ascii=False),
                json.dumps(providers or [], ensure_ascii=False),
            ),
        )
        self.conn.commit()
        return cursor.lastrowid

    def concluir_busca_vagas(self, search_id, result_count):
        self.conn.execute(
            "UPDATE job_searches SET result_count = ? WHERE id = ?",
            (int(result_count), search_id),
        )
        self.conn.commit()

    def salvar_vaga_encontrada(self, vaga, search_id=None, position=0):
        """Insere ou atualiza uma vaga normalizada sem perder decisões do usuário."""
        cursor = self.conn.cursor()
        values = (
            vaga.get("external_id", ""), vaga["titulo"], vaga.get("empresa", ""),
            vaga.get("localizacao", ""), vaga.get("modality", ""), vaga.get("seniority", ""),
            vaga.get("employment_type", ""), vaga.get("salary", ""), vaga.get("url", ""),
            vaga.get("descricao", ""), vaga.get("fonte", "Manual"), vaga["canonical_key"],
            int(vaga.get("rank_score", 0)), vaga.get("published_at", ""),
        )
        cursor.execute("""
            INSERT INTO job_listings(
                external_id, title, company, location, modality, seniority, employment_type,
                salary, url, description, provider, canonical_key, rank_score, published_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(canonical_key) DO UPDATE SET
                external_id=excluded.external_id, title=excluded.title, company=excluded.company,
                location=excluded.location, modality=excluded.modality, seniority=excluded.seniority,
                employment_type=excluded.employment_type, salary=excluded.salary, url=excluded.url,
                description=excluded.description, provider=excluded.provider,
                rank_score=excluded.rank_score, published_at=excluded.published_at,
                last_seen_at=CURRENT_TIMESTAMP
        """, values)
        listing = cursor.execute(
            "SELECT id, decision FROM job_listings WHERE canonical_key = ?", (vaga["canonical_key"],)
        ).fetchone()
        if search_id is not None:
            cursor.execute("""
                INSERT OR REPLACE INTO job_search_results(search_id, listing_id, position, rank_score)
                VALUES (?, ?, ?, ?)
            """, (search_id, listing["id"], int(position), int(vaga.get("rank_score", 0))))
        self.conn.commit()
        return listing["id"], listing["decision"]

    def definir_decisao_vaga(self, listing_id, decision):
        valid = {"nova", "favorita", "descartada", "candidatura"}
        if decision not in valid:
            raise ValueError("Decisão de vaga inválida.")
        self.conn.execute(
            "UPDATE job_listings SET decision = ?, last_seen_at=CURRENT_TIMESTAMP WHERE id = ?",
            (decision, listing_id),
        )
        self.conn.commit()

    def obter_vaga_encontrada(self, listing_id):
        return self.conn.execute("SELECT * FROM job_listings WHERE id = ?", (listing_id,)).fetchone()

    def listar_vagas_encontradas(self, decision=None, limite=100):
        if decision:
            return self.conn.execute(
                "SELECT * FROM job_listings WHERE decision = ? ORDER BY rank_score DESC, last_seen_at DESC LIMIT ?",
                (decision, limite),
            ).fetchall()
        return self.conn.execute(
            "SELECT * FROM job_listings ORDER BY last_seen_at DESC LIMIT ?", (limite,)
        ).fetchall()

    def converter_vaga_em_candidatura(self, listing_id, status="Preparando candidatura"):
        vaga = self.obter_vaga_encontrada(listing_id)
        if not vaga:
            raise ValueError("Vaga não encontrada.")
        existing = self.conn.execute(
            "SELECT id FROM opportunities WHERE listing_id = ?", (listing_id,)
        ).fetchone()
        if existing:
            return existing["id"]
        resume_id = self.obter_curriculo_ativo_id()
        cursor = self.conn.cursor()
        source_key = self._chave_oportunidade(
            vaga["title"], vaga["company"], vaga["provider"], vaga["url"]
        )
        cursor.execute("""
            INSERT INTO opportunities(
                titulo, empresa, plataforma, url, descricao, status, source_key, updated_at,
                listing_id, salary_range, work_model, employment_type, resume_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?)
        """, (
            vaga["title"], vaga["company"], vaga["provider"], vaga["url"], vaga["description"],
            status, source_key, listing_id, vaga["salary"], vaga["modality"],
            vaga["employment_type"], resume_id,
        ))
        opportunity_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO application_history(opportunity_id, status_to, notes) VALUES (?, ?, ?)",
            (opportunity_id, status, "Candidatura criada a partir da busca de vagas."),
        )
        cursor.execute("UPDATE job_listings SET decision='candidatura' WHERE id=?", (listing_id,))
        self.conn.commit()
        return opportunity_id

    def listar_historico_candidatura(self, opportunity_id):
        return self.conn.execute(
            "SELECT * FROM application_history WHERE opportunity_id=? ORDER BY created_at DESC, id DESC",
            (opportunity_id,),
        ).fetchall()

    def atualizar_candidatura(self, opportunity_id, **fields):
        allowed = {
            "status", "applied_at", "salary_range", "work_model", "employment_type",
            "recruiter_name", "recruiter_email", "recruiter_phone", "next_action",
            "next_action_at", "resume_id", "job_match_id", "notes",
        }
        updates = {key: value for key, value in fields.items() if key in allowed}
        if not updates:
            return
        current = self.obter_oportunidade(opportunity_id)
        if not current:
            raise ValueError("Candidatura não encontrada.")
        old_status = current["status"]
        assignments = ", ".join(f"{key}=?" for key in updates)
        self.conn.execute(
            f"UPDATE opportunities SET {assignments}, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (*updates.values(), opportunity_id),
        )
        new_status = updates.get("status", old_status)
        if new_status != old_status:
            self.conn.execute("""
                INSERT INTO application_history(opportunity_id, status_from, status_to, notes)
                VALUES (?, ?, ?, ?)
            """, (opportunity_id, old_status, new_status, updates.get("notes", "")))
        self.conn.commit()

    def candidaturas_para_acompanhamento(self, dias=0):
        modifier = f"+{int(dias)} day"
        return self.conn.execute("""
            SELECT * FROM opportunities
            WHERE next_action_at IS NOT NULL AND next_action_at != ''
              AND date(next_action_at) <= date('now', ?)
              AND status NOT IN ('Rejeitado', 'Encerrado')
            ORDER BY date(next_action_at), updated_at
        """, (modifier,)).fetchall()

    def metricas_candidaturas(self):
        total = self.conn.execute("SELECT COUNT(*) FROM opportunities").fetchone()[0]
        retorno = self.conn.execute("""
            SELECT COUNT(*) FROM opportunities
            WHERE status IN ('Triagem', 'Entrevista com RH', 'Entrevista técnica', 'Proposta')
        """).fetchone()[0]
        entrevistas = self.conn.execute("""
            SELECT COUNT(*) FROM opportunities
            WHERE status IN ('Entrevista com RH', 'Entrevista técnica', 'Proposta')
        """).fetchone()[0]
        by_status = self.conn.execute(
            "SELECT status, COUNT(*) AS total FROM opportunities GROUP BY status ORDER BY total DESC"
        ).fetchall()
        best_source = self.conn.execute("""
            SELECT plataforma, COUNT(*) AS total FROM opportunities
            WHERE status IN ('Entrevista com RH', 'Entrevista técnica', 'Proposta')
            GROUP BY plataforma ORDER BY total DESC LIMIT 1
        """).fetchone()
        average_days = self.conn.execute("""
            SELECT COALESCE(ROUND(AVG(julianday('now') - julianday(COALESCE(updated_at, created_at))), 1), 0)
            FROM opportunities WHERE status NOT IN ('Rejeitado', 'Encerrado')
        """).fetchone()[0]
        return {
            "total": total,
            "retorno": round((retorno / total * 100), 1) if total else 0,
            "entrevistas": round((entrevistas / total * 100), 1) if total else 0,
            "por_status": {row["status"]: row["total"] for row in by_status},
            "melhor_fonte": best_source["plataforma"] if best_source else "-",
            "dias_sem_atualizacao": average_days,
            "acompanhamentos": len(self.candidaturas_para_acompanhamento()),
        }

    # ==========================================================
    # V2: oportunidades, entrevistas e conversa
    # ==========================================================

    @staticmethod
    def _chave_oportunidade(titulo, empresa, plataforma, url):
        """Chave estável para evitar salvar duas vezes a mesma vaga."""
        texto = (url or "").strip().lower()
        if not texto:
            texto = "|".join((titulo or "", empresa or "", plataforma or "")).strip().lower()
        return hashlib.sha256(texto.encode("utf-8", errors="ignore")).hexdigest() if texto else None

    def salvar_oportunidade(self, titulo, empresa, plataforma, url, descricao, status="Salva"):
        chave = self._chave_oportunidade(titulo, empresa, plataforma, url)
        cursor = self.conn.cursor()
        existente = cursor.execute("SELECT id FROM opportunities WHERE source_key = ?", (chave,)).fetchone() if chave else None
        if existente:
            atual = cursor.execute("SELECT status FROM opportunities WHERE id = ?", (existente["id"],)).fetchone()
            cursor.execute("""
                UPDATE opportunities
                SET titulo=?, empresa=?, plataforma=?, url=?, descricao=?, status=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
            """, (titulo, empresa, plataforma, url, descricao, status, existente["id"]))
            if atual and atual["status"] != status:
                cursor.execute("""
                    INSERT INTO application_history(opportunity_id, status_from, status_to, notes)
                    VALUES (?, ?, ?, ?)
                """, (existente["id"], atual["status"], status, "Atualização manual."))
            self.conn.commit()
            return existente["id"]
        cursor.execute("""
            INSERT INTO opportunities (titulo, empresa, plataforma, url, descricao, status, source_key, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (titulo, empresa, plataforma, url, descricao, status, chave))
        oportunidade_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO application_history(opportunity_id, status_to, notes) VALUES (?, ?, ?)",
            (oportunidade_id, status, "Candidatura adicionada manualmente."),
        )
        self.conn.commit()
        return oportunidade_id

    def listar_oportunidades(self):
        cursor = self.conn.cursor()
        return cursor.execute("SELECT * FROM opportunities ORDER BY created_at DESC, id DESC").fetchall()

    def obter_oportunidade(self, oportunidade_id):
        return self.conn.execute("SELECT * FROM opportunities WHERE id = ?", (oportunidade_id,)).fetchone()

    def atualizar_status_oportunidade(self, oportunidade_id, status):
        self.atualizar_candidatura(oportunidade_id, status=status)

    def salvar_mensagem_assistente(self, role, content):
        self.conn.execute("INSERT INTO assistant_messages (role, content) VALUES (?, ?)", (role, content))
        self.conn.commit()

    def listar_mensagens_assistente(self, limite=20):
        cursor = self.conn.cursor()
        return cursor.execute("SELECT * FROM assistant_messages ORDER BY id DESC LIMIT ?", (limite,)).fetchall()

    def salvar_entrevista(self, pergunta, resposta, feedback, nota, tema):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO interview_sessions (pergunta, resposta, feedback, nota, tema)
            VALUES (?, ?, ?, ?, ?)
        """, (pergunta, resposta, feedback, nota, tema))
        self.conn.commit()
        return cursor.lastrowid

    def salvar_pacote_candidatura(self, oportunidade_id, pacote):
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO application_packages (opportunity_id, carta, resumo_direcionado, palavras_chave, checklist)
            VALUES (?, ?, ?, ?, ?)
        """, (
            oportunidade_id, pacote["carta"], pacote["resumo_direcionado"],
            json.dumps(pacote["palavras_chave"], ensure_ascii=False),
            json.dumps(pacote["checklist"], ensure_ascii=False),
        ))
        self.conn.commit()
        return cursor.lastrowid

    def limpar_historico(self):

        cursor = self.conn.cursor()

        caminhos = [row["caminho"] for row in cursor.execute("SELECT caminho FROM resumes").fetchall()]
        cursor.execute("DELETE FROM job_matches")
        cursor.execute("DELETE FROM jobs")
        cursor.execute("DELETE FROM resumes")

        cursor.execute(
            "DELETE FROM sqlite_sequence WHERE name='resumes'"
        )
        cursor.execute("DELETE FROM app_state WHERE key = 'active_resume_id'")
        self.conn.commit()
        for caminho in caminhos:
            self._remover_arquivo_curriculo(caminho)

    # ==========================================================
    # ANÁLISES DOS CURRÍCULOS
    # ==========================================================
    
    def salvar_analise(
        self,
        resume_id,
        cargo=None,
        area=None,
        senioridade=None,
        ats_score=None,
        hard_skills=None,
        soft_skills=None,
        tecnologias=None,
        idiomas=None,
        certificacoes=None,
        anos_experiencia=None,
        nivel_curriculo=None,
        palavras_chave=None,
        pontos_fortes=None,
        pontos_melhoria=None,
        competencias_faltantes=None,
        recomendacoes=None,
        resumo=None,
    ):

        cursor = self.conn.cursor()

        cursor.execute("""
        INSERT INTO resume_analysis
        (
            resume_id,
            cargo,
            area,
            senioridade,
            ats_score,
            hard_skills,
            soft_skills,
            tecnologias,
            idiomas,
            certificacoes,
            anos_experiencia,
            nivel_curriculo,
            palavras_chave,
            pontos_fortes,
            pontos_melhoria,
            competencias_faltantes,
            recomendacoes,
            resumo
        )
        VALUES
        (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
        """, (
            resume_id,
            cargo,
            area,
            senioridade,
            ats_score,
            hard_skills,
            soft_skills,
            tecnologias,
            idiomas,
            certificacoes,
            anos_experiencia,
            nivel_curriculo,
            palavras_chave,
            pontos_fortes,
            pontos_melhoria,
            competencias_faltantes,
            recomendacoes,
            resumo
        ))

        self.conn.commit()
        self.definir_curriculo_ativo(resume_id)

    def obter_analise(self, resume_id):

        cursor = self.conn.cursor()

        cursor.execute("""
        SELECT *
        FROM resume_analysis
        WHERE resume_id = ?
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        """, (resume_id,))

        return cursor.fetchone()

    def listar_analises(self):

        cursor = self.conn.cursor()

        cursor.execute("""
        SELECT *
        FROM resume_analysis
        ORDER BY created_at DESC
        """)

        return cursor.fetchall()

    def listar_historico(self):

        cursor = self.conn.cursor()

        cursor.execute("""
        SELECT
            r.id,
            r.nome_arquivo,
            r.data_importacao,
            a.cargo,
            a.area,
            a.senioridade,
            a.ats_score
        FROM resumes r
        LEFT JOIN resume_analysis a
            ON a.resume_id = r.id
        ORDER BY r.data_importacao DESC
        """)

        return cursor.fetchall()

    def excluir_analise(self, resume_id):

        cursor = self.conn.cursor()

        cursor.execute(
            "DELETE FROM resume_analysis WHERE resume_id = ?",
            (resume_id,)
        )

        self.conn.commit()

    # ==========================================================
    # DASHBOARD
    # ==========================================================

    def dashboard_total_curriculos(self):

        cursor = self.conn.cursor()

        cursor.execute("""
        SELECT COUNT(*)
        FROM resumes
        """)

        return cursor.fetchone()[0]


    def dashboard_media_ats(self):

        cursor = self.conn.cursor()

        cursor.execute("""
        SELECT ROUND(AVG(ats_score),0)
        FROM resume_analysis
        WHERE ats_score IS NOT NULL
        """)

        valor = cursor.fetchone()[0]

        return valor or 0


    def dashboard_ultima_analise(self):

        cursor = self.conn.cursor()

        cursor.execute("""
        SELECT
            cargo,
            created_at
        FROM resume_analysis
        ORDER BY created_at DESC
        LIMIT 1
        """)

        return cursor.fetchone()


    def dashboard_ultimas_analises(self, limite=5):

        cursor = self.conn.cursor()

        cursor.execute("""
        SELECT
            cargo,
            ats_score,
            created_at
        FROM resume_analysis
        ORDER BY created_at DESC
        LIMIT ?
        """, (limite,))

        return cursor.fetchall()

    def dashboard_job_match_metricas(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) AS total, COALESCE(ROUND(AVG(compatibilidade), 0), 0) AS media
            FROM job_matches
        """)
        return cursor.fetchone()


import sqlite3
from pathlib import Path


class Database:

    def __init__(self):
        Path("data").mkdir(exist_ok=True)

        self.conn = sqlite3.connect("data/ai_career_agent.db")
        self.conn.row_factory = sqlite3.Row

        self.criar_tabelas()

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

        self.conn.commit()
     

       
    # ==========================================================
    # CURRÍCULOS
    # ==========================================================

    def salvar_curriculo(self, nome, caminho, texto):

        cursor = self.conn.cursor()

        cursor.execute("""
        INSERT INTO resumes
        (
            nome_arquivo,
            caminho,
            texto
        )
        VALUES
        (
            ?, ?, ?
        )
        """, (nome, caminho, texto))

        self.conn.commit()

        return cursor.lastrowid

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

        cursor.execute(
            "DELETE FROM resumes WHERE id=?",
            (resume_id,)
        )

        cursor.execute("SELECT COUNT(*) FROM resumes")

        total = cursor.fetchone()[0]

        if total == 0:
            cursor.execute(
                "DELETE FROM sqlite_sequence WHERE name='resumes'"
            )

        self.conn.commit()

    def limpar_historico(self):

        cursor = self.conn.cursor()

        cursor.execute("DELETE FROM resumes")

        cursor.execute(
            "DELETE FROM sqlite_sequence WHERE name='resumes'"
        )

        self.conn.commit()

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

    def obter_analise(self, resume_id):

        cursor = self.conn.cursor()

        cursor.execute("""
        SELECT *
        FROM resume_analysis
        WHERE resume_id = ?
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


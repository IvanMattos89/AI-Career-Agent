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

        self.conn.commit()

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
        WHERE id=?
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

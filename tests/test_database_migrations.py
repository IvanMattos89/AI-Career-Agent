import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.database.sqlite_db import Database


class DatabaseMigrationTest(unittest.TestCase):
    def test_upgrades_legacy_database_without_losing_opportunity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "legacy.db"
            connection = sqlite3.connect(path)
            connection.executescript("""
                CREATE TABLE opportunities(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    titulo TEXT NOT NULL,
                    empresa TEXT,
                    plataforma TEXT NOT NULL DEFAULT 'Manual',
                    url TEXT,
                    descricao TEXT,
                    status TEXT NOT NULL DEFAULT 'Salva',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                INSERT INTO opportunities(titulo, empresa) VALUES('Analista Fiscal', 'Empresa');
                CREATE TABLE application_packages(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    opportunity_id INTEGER NOT NULL,
                    carta TEXT NOT NULL,
                    resumo_direcionado TEXT NOT NULL,
                    palavras_chave TEXT NOT NULL DEFAULT '[]',
                    checklist TEXT NOT NULL DEFAULT '[]',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            connection.commit()
            connection.close()

            with (
                patch("app.database.sqlite_db.DATA_DIR", root),
                patch("app.database.sqlite_db.DATABASE", path),
                patch("app.database.sqlite_db.RESUMES_DIR", root / "resumes"),
            ):
                database = Database()
                versions = [row[0] for row in database.conn.execute(
                    "SELECT version FROM schema_migrations ORDER BY version"
                )]
                opportunity = database.listar_oportunidades()[0]
                package_columns = {
                    row[1] for row in database.conn.execute("PRAGMA table_info(application_packages)")
                }
                resume_columns = {
                    row[1] for row in database.conn.execute("PRAGMA table_info(resumes)")
                }
                backup = database.criar_backup(root / "backup.db")
                diagnostic = database.diagnostico()
                analysis_columns = {
                    row[1] for row in database.conn.execute(
                        "PRAGMA table_info(resume_analysis)"
                    )
                }
                database.close()

            self.assertEqual(versions, [1, 2, 3, 4, 5, 7, 8])
            self.assertEqual(opportunity["titulo"], "Analista Fiscal")
            self.assertIn("resume_id", package_columns)
            self.assertIn("structured_json", resume_columns)
            self.assertIn("confianca", analysis_columns)
            self.assertTrue(backup.is_file())
            self.assertEqual(diagnostic["integridade"], "ok")
            self.assertEqual(diagnostic["violacoes_fk"], 0)


if __name__ == "__main__":
    unittest.main()

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.database.sqlite_db import Database


class ActiveResumeDatabaseTest(unittest.TestCase):
    def test_active_resume_is_explicit_and_deletion_removes_managed_copy(self):
        with tempfile.TemporaryDirectory() as pasta:
            raiz = Path(pasta)
            banco = raiz / "career.db"
            curriculos = raiz / "resumes"
            curriculos.mkdir()
            arquivo = curriculos / "curriculo.docx"
            arquivo.write_bytes(b"arquivo de teste")

            with patch("app.database.sqlite_db.DATABASE", banco), patch("app.database.sqlite_db.DATA_DIR", raiz), patch("app.database.sqlite_db.RESUMES_DIR", curriculos):
                db = Database()
                primeiro = db.salvar_curriculo("primeiro.docx", str(arquivo), "Analista Fiscal com ICMS")
                db.salvar_analise(
                    primeiro, cargo="Analista Fiscal", area="Fiscal", senioridade="Pleno",
                    confianca=0.85, ats_score=80,
                )
                segundo = db.salvar_curriculo("segundo.docx", str(curriculos / "segundo.docx"), "Analista de Dados com SQL")
                db.salvar_analise(segundo, cargo="Analista de Dados", area="Dados", senioridade="Pleno", ats_score=80)

                db.definir_curriculo_ativo(primeiro)
                self.assertEqual(db.obter_analise_ativa()["resume_id"], primeiro)
                self.assertEqual(db.obter_analise_ativa()["confianca"], 0.85)
                self.assertTrue(db.excluir_curriculo(primeiro))
                self.assertFalse(arquivo.exists())
                self.assertEqual(db.obter_curriculo_ativo_id(), segundo)
                db.close()

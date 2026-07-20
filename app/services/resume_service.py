from pathlib import Path
from shutil import copy2

from docx import Document
from pypdf import PdfReader

from app.database.sqlite_db import Database


class ResumeService:

    def __init__(self):
        self.resume_dir = Path("data/resumes")
        self.resume_dir.mkdir(parents=True, exist_ok=True)

        self.db = Database()

    def importar(self, arquivo):

        origem = Path(arquivo)

        destino = self.resume_dir / origem.name

        copy2(origem, destino)

        texto = self.ler(destino)

        resume_id = self.db.salvar_curriculo(
            destino.name,
            str(destino),
            texto
        )

        return resume_id, destino, texto

    def ler(self, arquivo):

        arquivo = Path(arquivo)

        if arquivo.suffix.lower() == ".docx":
            return self._ler_docx(arquivo)

        if arquivo.suffix.lower() == ".pdf":
            return self._ler_pdf(arquivo)

        raise ValueError("Formato não suportado.")

    def _ler_docx(self, arquivo):

        documento = Document(arquivo)

        return "\n".join(
            p.text
            for p in documento.paragraphs
        )

    def _ler_pdf(self, arquivo):

        reader = PdfReader(str(arquivo))

        texto = []

        for pagina in reader.pages:

            conteudo = pagina.extract_text()

            if conteudo:
                texto.append(conteudo)

        return "\n".join(texto)
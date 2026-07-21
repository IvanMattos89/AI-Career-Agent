"""Workers para manter chamadas potencialmente lentas fora da thread da interface."""

from PySide6.QtCore import QObject, Signal, Slot


class JobMatchWorker(QObject):
    finished = Signal(dict)
    failed = Signal(str)

    def __init__(self, descricao, titulo=None):
        super().__init__()
        self.descricao = descricao
        self.titulo = titulo

    @Slot()
    def run(self):
        try:
            # O serviço (e a conexão SQLite) é criado dentro da thread correta.
            from app.services.job_match_service import JobMatchService
            self.finished.emit(JobMatchService().comparar(self.descricao, self.titulo))
        except Exception as erro:
            self.failed.emit(str(erro))


class JobSearchWorker(QObject):
    finished = Signal(list)
    failed = Signal(str)

    def __init__(self, termo=None, para_curriculo=False, estado="", cidade=""):
        super().__init__()
        self.termo = termo
        self.para_curriculo = para_curriculo
        self.estado = estado
        self.cidade = cidade

    @Slot()
    def run(self):
        try:
            from app.services.job_search_service import JobSearchService
            service = JobSearchService()
            if self.para_curriculo:
                resultado = service.buscar_para_curriculo(estado=self.estado, cidade=self.cidade)
                self.finished.emit(resultado["vagas"])
            else:
                self.finished.emit(service.buscar(self.termo, estado=self.estado, cidade=self.cidade))
        except Exception as erro:
            self.failed.emit(str(erro))


class JobBatchMatchWorker(QObject):
    progress = Signal(int, int, int, str)
    finished = Signal(list)
    failed = Signal(str)

    def __init__(self, vagas):
        super().__init__()
        self.vagas = vagas

    @Slot()
    def run(self):
        try:
            from app.services.job_match_service import JobMatchService
            service = JobMatchService()
            resultados = []
            total = len(self.vagas)
            for indice, vaga in enumerate(self.vagas):
                if self.thread().isInterruptionRequested():
                    break
                try:
                    resultado = service.comparar(vaga["descricao"], vaga.get("titulo"))
                    resultados.append(resultado)
                    self.progress.emit(indice, total, resultado["compatibilidade"], "")
                except Exception as erro:
                    self.progress.emit(indice, total, -1, str(erro))
            self.finished.emit(resultados)
        except Exception as erro:
            self.failed.emit(str(erro))


class OllamaStatusWorker(QObject):
    finished = Signal(bool, str)

    def __init__(self, url):
        super().__init__()
        self.url = url.rstrip("/")

    @Slot()
    def run(self):
        try:
            import requests
            response = requests.get(f"{self.url}/api/tags", timeout=5)
            response.raise_for_status()
            self.finished.emit(True, "Ollama disponível")
        except Exception as erro:
            self.finished.emit(False, f"Ollama indisponível: {erro}")


class ResumeAnalysisWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, resume_id, texto):
        super().__init__()
        self.resume_id = resume_id
        self.texto = texto

    @Slot()
    def run(self):
        try:
            from app.services.analysis_service import AnalysisService
            self.finished.emit(AnalysisService().analisar_texto(self.resume_id, self.texto))
        except Exception as erro:
            self.failed.emit(str(erro))


class ResumeImportWorker(QObject):
    """Copia e extrai o currículo fora da thread da interface."""
    finished = Signal(int, str, str)
    failed = Signal(str)

    def __init__(self, arquivo):
        super().__init__()
        self.arquivo = arquivo

    @Slot()
    def run(self):
        try:
            from app.services.resume_service import ResumeService
            resultado = ResumeService().importar(self.arquivo)
            self.finished.emit(resultado.resume_id, str(resultado.destination), resultado.text)
        except (FileNotFoundError, PermissionError, ValueError, OSError) as erro:
            self.failed.emit(str(erro))
        except Exception:
            from app.ai.logging_config import logger
            logger.exception("Falha inesperada durante a importação de currículo")
            self.failed.emit("Não foi possível importar o currículo. Consulte o log para mais detalhes.")


class CareerWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, operacao, *args):
        super().__init__()
        self.operacao = operacao
        self.args = args

    @Slot()
    def run(self):
        try:
            if self.operacao == "gerar_pacote":
                from app.services.application_studio_service import ApplicationStudioService
                service = ApplicationStudioService()
            else:
                from app.services.career_assistant_service import CareerAssistantService
                service = CareerAssistantService()
            self.finished.emit(getattr(service, self.operacao)(*self.args))
        except Exception as erro:
            self.failed.emit(str(erro))

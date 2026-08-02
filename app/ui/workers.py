"""Workers e ciclo de vida de tarefas executadas fora da thread da interface."""

from collections.abc import Iterable
from typing import Any

from PySide6.QtCore import QObject, Signal, Slot

from app.ai.logging_config import logger


def shutdown_threads(threads: Iterable[Any], timeout_ms: int = 3000) -> None:
    """Encerra threads de interface sem deixá-las serem destruídas em execução.

    ``quit`` é cooperativo e não interrompe uma requisição bloqueante já iniciada.
    Nunca usamos ``terminate`` porque a thread pode estar gravando no SQLite.
    """
    active = [thread for thread in threads if thread is not None and thread.isRunning()]
    for thread in active:
        thread.requestInterruption()
        thread.quit()

    for thread in active:
        if thread.wait(timeout_ms):
            continue
        logger.warning(
            "Thread ainda ativa após %sms; aguardando encerramento seguro", timeout_ms
        )
        thread.wait()


class JobMatchWorker(QObject):
    finished = Signal(dict)
    failed = Signal(str)

    def __init__(self, descricao, titulo=None):
        super().__init__()
        self.descricao = descricao
        self.titulo = titulo

    @Slot()
    def run(self):
        service: Any = None
        try:
            # O serviço (e a conexão SQLite) é criado dentro da thread correta.
            from app.services.job_match_service import JobMatchService
            service = JobMatchService()
            self.finished.emit(service.comparar(self.descricao, self.titulo))
        except Exception as erro:
            self.failed.emit(str(erro))
        finally:
            if service is not None:
                service.db.close()


class JobSearchWorker(QObject):
    finished = Signal(list)
    failed = Signal(str)

    def __init__(
        self, termo=None, para_curriculo=False, estado="", cidade="",
        modalidade="", senioridade="",
    ):
        super().__init__()
        self.termo = termo
        self.para_curriculo = para_curriculo
        self.estado = estado
        self.cidade = cidade
        self.modalidade = modalidade
        self.senioridade = senioridade

    @Slot()
    def run(self):
        service = None
        try:
            from app.services.job_search_service import JobSearchService
            service = JobSearchService()
            if self.para_curriculo:
                resultado = service.buscar_para_curriculo(
                    estado=self.estado, cidade=self.cidade,
                    modalidade=self.modalidade, senioridade=self.senioridade,
                )
                self.finished.emit(resultado["vagas"])
            else:
                self.finished.emit(service.buscar(
                    self.termo, estado=self.estado, cidade=self.cidade,
                    modalidade=self.modalidade, senioridade=self.senioridade,
                ))
        except Exception as erro:
            self.failed.emit(str(erro))
        finally:
            if service is not None:
                service.db.close()


class JobBatchMatchWorker(QObject):
    progress = Signal(int, int, int, str)
    finished = Signal(list)
    failed = Signal(str)

    def __init__(self, vagas):
        super().__init__()
        self.vagas = vagas

    @Slot()
    def run(self):
        service = None
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
        finally:
            if service is not None:
                service.db.close()


class OllamaStatusWorker(QObject):
    finished = Signal(bool, str)

    def __init__(self, url, model=""):
        super().__init__()
        self.url = url.rstrip("/")
        self.model = model.strip()

    @Slot()
    def run(self):
        try:
            import requests
            response = requests.get(f"{self.url}/api/tags", timeout=5)
            response.raise_for_status()
            models = {
                str(item.get("name") or item.get("model") or "").strip()
                for item in response.json().get("models", [])
            }
            if self.model and self.model not in models:
                self.finished.emit(
                    False,
                    f"Ollama disponível, mas o modelo '{self.model}' não está instalado.",
                )
            else:
                self.finished.emit(True, f"Ollama disponível · modelo {self.model or 'detectado'}")
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
        service = None
        try:
            from app.services.analysis_service import AnalysisService
            service = AnalysisService()
            self.finished.emit(service.analisar_texto(self.resume_id, self.texto))
        except Exception as erro:
            self.failed.emit(str(erro))
        finally:
            if service is not None:
                service.db.close()


class ResumeImportWorker(QObject):
    """Copia e extrai o currículo fora da thread da interface."""
    finished = Signal(int, str, str)
    failed = Signal(str)

    def __init__(self, arquivo):
        super().__init__()
        self.arquivo = arquivo

    @Slot()
    def run(self):
        service = None
        try:
            from app.services.resume_service import ResumeService
            service = ResumeService()
            resultado = service.importar(self.arquivo)
            self.finished.emit(resultado.resume_id, str(resultado.destination), resultado.text)
        except (FileNotFoundError, PermissionError, ValueError, OSError) as erro:
            self.failed.emit(str(erro))
        except Exception:
            from app.ai.logging_config import logger
            logger.exception("Falha inesperada durante a importação de currículo")
            self.failed.emit("Não foi possível importar o currículo. Consulte o log para mais detalhes.")
        finally:
            if service is not None:
                service.db.close()


class CareerWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, operacao, *args):
        super().__init__()
        self.operacao = operacao
        self.args = args

    @Slot()
    def run(self):
        service: Any = None
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
        finally:
            if service is not None:
                service.db.close()

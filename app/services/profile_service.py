from app.ai.models import ResumeAnalysis


class ProfileService:

    def __init__(self):
        self.analysis = None

    def atualizar(self, analysis: ResumeAnalysis):
        self.analysis = analysis

    def obter(self):
        return self.analysis

    def possui_perfil(self):
        return self.analysis is not None

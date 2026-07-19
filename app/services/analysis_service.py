from app.ai.analyzer import ResumeAnalyzer


class AnalysisService:

    def __init__(self):
        self.analyzer = ResumeAnalyzer()

    def analisar_texto(self, texto):
        return self.analyzer.analisar(texto)

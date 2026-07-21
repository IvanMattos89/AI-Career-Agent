"""Ferramenta manual de diagnóstico de importação; não faz parte dos testes."""

from app.services.resume_service import ResumeService


def executar():
    arquivo = input("Digite o caminho do currículo (.pdf ou .docx): ")
    resultado = ResumeService().importar(arquivo)
    print("Arquivo copiado para:")
    print(resultado.destination)
    print("\n========== CONTEÚDO ==========\n")
    print(resultado.text)


if __name__ == "__main__":
    executar()

from app.services.resume_service import ResumeService

service = ResumeService()

arquivo = input("Digite o caminho do currículo (.docx): ")

novo = service.import_resume(arquivo)

print("Arquivo copiado para:")
print(novo)

texto = service.read_docx(novo)

print("\n========== CONTEÚDO ==========\n")
print(texto)
# Histórico de versões

## 3.4.0 - 2026-08-01

- Detector de competências com limites de palavra e remoção de falsos positivos.
- Cálculo de experiência pelos períodos e certificações verificadas por contexto.
- Migrations 4 e 5 com reparo de vínculos, confiança persistida e novas chaves de vagas.
- Busca paralela por provedor, localização brasileira e modalidades normalizadas.
- Deduplicação ampliada para variações de título, empresa e localização.
- Prompts protegidos contra instruções contidas em vagas e currículos.
- Cache de disponibilidade do Ollama e preservação das regras em prompts extensos.
- Encerramento seguro de threads sem finalização forçada durante gravações.
- Campo protegido para chave OpenAI e validação do modelo instalado no Ollama.
- Logs rotativos e dados em LocalAppData na versão empacotada.
- Exportação Word com escolha explícita do destino e configuração PyInstaller.

## 3.3.0 - 2026-08-01

- Currículo estruturado com reconhecimento de títulos usados no Brasil.
- Preservação integral do conteúdo durante a geração do currículo direcionado.
- Matriz de requisitos, evidências e ações, sem inclusão automática de informações não comprovadas.
- Título, resumo e ordem das competências direcionados à vaga.
- Pré-visualização editável antes da exportação em Word ou PDF.
- Modelo A4 de uma coluna, compacto e compatível com ATS.
- Job Match enriquecido com a trajetória profissional completa.
- Busca recomendada consolidando todos os cargos equivalentes, com deduplicação final.
- Correção dos limites de palavras no analisador local.
- Encerramento seguro das tarefas em segundo plano.

## 3.2.0

- Busca unificada, decisões sobre vagas e pipeline de candidaturas.
- Métricas de provedores, configurações e recursos locais de privacidade.

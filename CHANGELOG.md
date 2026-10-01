# Histórico de versões

## 2026-09-30 — perfis e consistência das evidências

- Conversas, entrevistas, objetivos e confirmações vinculados ao currículo; exclusão remove seus registros.
- Histórico legado sem perfil isolado do contexto e excluível pela Central de Carreira.
- Evidências compartilhadas distinguem experiência relatada, curso, menção, negativa, conflito e ausência.
- Inventário mantém requisitos desconhecidos, separa prioridades e impede nota completa em análise parcial.
- Senioridade usa períodos profissionais e responsabilidades com evidências; tempo sozinho não define nível.
- Completude de cinco seções, com teto de 100, sem favorecer tempo de carreira ou volume de habilidades.
- Teste de fallback valida a chamada com timeout antes de simular a falha.

## Em desenvolvimento — confiabilidade das avaliações

- Job Match valida formato e tipos da resposta da IA e usa fallback local em falhas.
- Informações ausentes ficam pendentes; somente o usuário confirma lacunas com evidência.
- Recomendações priorizar/investigar/descartar incluem justificativa e próximo passo.
- Histórico e relatórios preservam pendências, evidências e decisões sem inventar nota.
- Senioridade local não presume Júnior por falta de informação nem usa idade ou curso como experiência.
- Entrevistas sem avaliação válida ficam sem nota; assistente utiliza objetivo editável e histórico recente.
- Recomendações não elevam a completude documental; este indicador é separado do Job Match.
- Validação local padronizada em pytest, com regressões para entradas inválidas e resultados pendentes.

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


## Busca: localização, consultas e diagnóstico — 2026-10-01

- Municípios do IBGE disponíveis offline e aproveitamento da localização estruturada dos provedores; remoção do país brasileiro presumido na Gupy.
- Vagas remotas nacionais independem do filtro de escritório; restrições regionais continuam aplicadas. Opção para incluir modalidade desconhecida.
- Cargos configurados consultados primeiro, limite ajustável e lista explícita de consultas omitidas.
- Diagnóstico persistido por busca e consolidado entre títulos, separando configuração, falhas, resposta vazia, filtros, duplicatas, descarte e limite; migração 9 preserva o histórico.
- Sem alteração de paginação ou fontes habilitadas por padrão.

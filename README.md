# AI Career Agent 3.4

Aplicação desktop para analisar currículos, encontrar vagas brasileiras, comparar aderência e organizar candidaturas com privacidade local.

## Direcionamento de carreira

As [orientações do agente neste repositório](AGENTS.md) foram atualizadas em 27/09/2026.
O [documento de referência](docs/AI_Career_Agent_atualizado.md) reúne o objetivo de
Analista Fiscal/Tributário Sênior, a evolução para Especialista, o plano de 90 dias,
o histórico de oportunidades e as pendências de validação. Os registros de vagas
e remuneração são históricos, sem confirmação externa de disponibilidade atual.
A [matriz de competências](docs/matriz_competencias.md) orienta a validação do perfil com evidências. As análises terminam em priorizar, investigar ou descartar; o plano combina frentes paralelas e revisões semanais e mensais.
Essa aplicação documental não altera os prompts ou o banco do aplicativo desktop.
As rotinas diárias e semanais estão documentadas; ativação e horários não foram verificados.

## Recursos

- Importação assíncrona de currículos PDF e DOCX.
- Análise ATS com Ollama, OpenAI mediante consentimento e fallback local.
- Currículo ativo explícito para buscas e comparações.
- Busca unificada em Vagas.com, Remotive, Gupy, Adzuna, Jooble e boards públicos Greenhouse/Lever.
- Filtros por cargo, estado, cidade, modalidade e senioridade, com ranking personalizado.
- Deduplicação entre fontes e decisões persistentes para favoritar ou descartar vagas.
- Job Match individual ou em lote, com histórico persistente.
- Currículo direcionado com prévia editável, matriz requisito × evidência e exportação ATS em DOCX/PDF.
- Conversão de uma vaga encontrada em candidatura com um clique.
- Pipeline com etapas, contatos, salário, prazo, próxima ação e histórico de alterações.
- Dashboard com taxa de retorno, entrevistas, fonte eficiente e alertas de acompanhamento.
- Configurações organizadas por IA, fontes e privacidade, com diagnóstico e backup consistente do SQLite.
- Exclusão completa da cópia interna do currículo e dados relacionados.

## Instalação

Requisitos: Windows 10 ou superior, Python 3.11+ e, opcionalmente, Ollama.

```powershell
git clone https://github.com/IvanMattos89/AI-Career-Agent.git
cd AI-Career-Agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python run.py
```

## Fluxo recomendado

1. Importe o currículo em **Meu currículo**.
2. Revise a análise em **Análise IA**.
3. Em **Histórico**, escolha qual currículo será usado como ativo.
4. Em **Buscar vagas**, selecione estado/cidade e busque para o currículo ativo.
5. Compare as vagas e abra a prévia do currículo direcionado.
6. Revise a matriz de evidências e edite o conteúdo antes de salvar em Word ou PDF.
7. Acompanhe as candidaturas na **Central de Carreira**.

## Avaliações com evidências

Job Match, adaptação e assistente usam a mesma camada de evidências, baseada no texto
original do currículo. Cada competência registra origem, trecho, tipo (experiência relatada,
curso, menção, negativa, conflito ou ausência) e confirmação do usuário, quando existente.
Curso ou academia FI não comprova operação, configuração ou implantação SAP. Confirmações
de lacuna feitas no Job Match, com fonte/data, são guardadas por currículo e compartilhadas
com os demais serviços. Uma evidência profissional continua sendo relato, sem verificação externa.

O Job Match exibe um inventário de trechos obrigatórios, desejáveis, condições e itens a
confirmar. Trechos desconhecidos não desaparecem: enquanto houver avaliação parcial ou
competências pendentes, não há pontuação. Quando disponível, a porcentagem se refere aos
requisitos identificados; a extração é heurística e exige revisão do anúncio integral.
A recomendação termina em **priorizar**, **investigar** ou **descartar**, com justificativa
e próximo passo. Priorizar ou descartar exige revisão documentada das condições pelo usuário.
Histórico e relatórios preservam as evidências e a abrangência; registros antigos devem ser reavaliados.

Conversas, entrevistas, objetivos e confirmações ficam vinculados ao currículo selecionado.
Trocar o currículo limpa a conversa e a entrevista visíveis e carrega o histórico correto;
respostas em andamento continuam vinculadas ao perfil de origem. Excluir o currículo remove
seus registros vinculados. Registros antigos sem vínculo permanecem isolados e nunca entram
no contexto de um perfil: o botão **Apagar conversas e entrevistas antigas sem vínculo com perfil**,
na Central de Carreira, remove esses registros e o objetivo global legado após confirmação.
O assistente usa até dez mensagens recentes do perfil; sem análise de currículo, solicita importação.

Senioridade considera períodos profissionais (sem duplicar meses sobrepostos) e sinais de
autonomia, complexidade e responsabilidade; dez anos isolados não bastam para Sênior.
A tela de análise registra as evidências e limitações. A **completude documental** usa cinco
seções de 20 pontos: identificação/contato, objetivo/resumo, trajetória declarada, formação
e competências declaradas. Primeira oportunidade explicitada preenche trajetória; a escala
atinge 100 sem premiar anos de experiência ou quantidade de competências. Seções não
reconhecidas requerem revisão. Nenhuma dessas notas estima chance de contratação.

As migrações preservam o histórico. Reanalise currículos antigos para obter os novos critérios
com evidências; notas antigas não são recalculadas silenciosamente.

## Provedores configuráveis

Vagas.com, Remotive e Arbeitnow funcionam sem configuração adicional. Para consultar boards
públicos de empresas que usam Greenhouse ou Lever, informe em **Configurações** os identificadores
separados por vírgula. Eles também podem ser definidos no `.env`:

```dotenv
JOB_GREENHOUSE_BOARDS=empresa-a,empresa-b
JOB_LEVER_SITES=empresa-a,empresa-b
JOB_ENABLE_ARBEITNOW=false
JOB_TARGET_TITLES=Analista Fiscal Sênior,Especialista Fiscal
GUPY_API_TOKEN=
ADZUNA_APP_ID=
ADZUNA_APP_KEY=
JOOBLE_API_KEY=
```

O Arbeitnow fica desativado por padrão porque a maioria de suas vagas remotas não declara
elegibilidade específica para o Brasil. A tela **Configurações** mostra recebidas, elegíveis no
Brasil e falhas por provedor.

A API da Gupy consulta somente as vagas da organização associada ao token. Greenhouse e Lever
também são APIs por empresa, portanto os respectivos identificadores precisam ser informados.
Adzuna e Jooble exigem cadastro próprio para emissão das chaves. LinkedIn e Indeed permanecem
como pesquisas abertas no navegador; o aplicativo não realiza scraping nem automatiza login.

## Privacidade

- Currículos e análises ficam em `data/`, somente no computador do usuário.
- OpenAI e Ollama remoto exigem consentimento explícito em **Configurações**.
- Currículos, banco, relatórios, logs e `.env` são ignorados pelo Git.
- A exclusão de um currículo remove banco, análises, matches e a cópia gerenciada pelo app; o arquivo original permanece intacto.
- Candidaturas, históricos e materiais de candidatura vinculados ao currículo também são removidos. Pacotes legados sem vínculo identificável são apagados por segurança.
- O armazenamento é local, mas não é criptografado em repouso. Proteja a conta do Windows e o acesso à pasta `data/`.

## Desenvolvimento

```powershell
pip install -r requirements-dev.txt
python -m pip check
python -m compileall -q app
python -m ruff check .
python -m mypy app
python -m pytest --cov=app --cov-report=term --cov-fail-under=70
```

No Windows, `scripts/check.ps1 -Install` prepara o ambiente e executa essas verificações.

O workflow em `.github/workflows/ci.yml` executa lint, compilação e testes no Windows.

## Limitações

- Plataformas fechadas podem exigir login e são abertas no navegador.
- Fontes públicas podem alterar seus formatos e ficar temporariamente indisponíveis.
- Todo material gerado deve ser revisado antes de uma candidatura.
- O gerador nunca adiciona automaticamente um requisito sem evidência no currículo importado.
- O modelo de currículo prioriza leitura ATS: A4, uma coluna, fonte legível e sem elementos gráficos.

## Executável Windows

Após instalar as dependências de desenvolvimento, execute:

```powershell
.\scripts\build_windows.ps1
```

O executável é criado em `dist/AI-Career-Agent.exe`. Na versão empacotada, banco, currículos,
relatórios e logs são armazenados em `%LOCALAPPDATA%\AI Career Agent`, evitando gravações em
`Program Files`. Assinatura digital e instalador devem ser aplicados antes da distribuição pública.

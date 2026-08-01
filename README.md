# AI Career Agent 3.2

Aplicação desktop para analisar currículos, encontrar vagas brasileiras, comparar aderência e organizar candidaturas com privacidade local.

## Recursos

- Importação assíncrona de currículos PDF e DOCX.
- Análise ATS com Ollama, OpenAI mediante consentimento e fallback local.
- Currículo ativo explícito para buscas e comparações.
- Busca unificada em Vagas.com, Remotive, Arbeitnow e boards públicos Greenhouse/Lever.
- Filtros por cargo, estado, cidade, modalidade e senioridade, com ranking personalizado.
- Deduplicação entre fontes e decisões persistentes para favoritar ou descartar vagas.
- Job Match individual ou em lote, com histórico persistente.
- Currículo direcionado e relatórios em DOCX/PDF.
- Conversão de uma vaga encontrada em candidatura com um clique.
- Pipeline com etapas, contatos, salário, prazo, próxima ação e histórico de alterações.
- Dashboard com taxa de retorno, entrevistas, fonte eficiente e alertas de acompanhamento.
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
5. Compare as vagas e gere o currículo direcionado.
6. Acompanhe as candidaturas na **Central de Carreira**.

## Provedores configuráveis

Vagas.com, Remotive e Arbeitnow funcionam sem configuração adicional. Para consultar boards
públicos de empresas que usam Greenhouse ou Lever, informe em **Configurações** os identificadores
separados por vírgula. Eles também podem ser definidos no `.env`:

```dotenv
JOB_GREENHOUSE_BOARDS=empresa-a,empresa-b
JOB_LEVER_SITES=empresa-a,empresa-b
```

## Privacidade

- Currículos e análises ficam em `data/`, somente no computador do usuário.
- OpenAI e Ollama remoto exigem consentimento explícito em **Configurações**.
- Currículos, banco, relatórios, logs e `.env` são ignorados pelo Git.
- A exclusão de um currículo remove banco, análises, matches e a cópia gerenciada pelo app; o arquivo original permanece intacto.

## Desenvolvimento

```powershell
pip install -r requirements-dev.txt
python -m ruff check app tests
python -m unittest discover -s tests -v
```

O workflow em `.github/workflows/ci.yml` executa lint, compilação e testes no Windows.

## Limitações

- Plataformas fechadas podem exigir login e são abertas no navegador.
- Fontes públicas podem alterar seus formatos e ficar temporariamente indisponíveis.
- Todo material gerado deve ser revisado antes de uma candidatura.

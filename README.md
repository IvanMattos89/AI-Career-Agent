# AI Career Agent

Aplicação desktop para analisar currículos, encontrar vagas brasileiras, comparar aderência e organizar candidaturas.

## Estado atual — versão 3.1

- Importação segura e assíncrona de PDF/DOCX.
- Análise de currículo com IA opcional e fallback local.
- Job Match, explicação da nota e histórico persistente.
- Busca brasileira por cargo, estado e cidade.
- Currículo direcionado à vaga, exportável em DOCX e PDF sem alterar o original.
- Central de Carreira com oportunidades, pipeline, entrevista e materiais de candidatura.

## Instalação

Requisitos: Windows 10+, Python 3.11+ e, opcionalmente, Ollama.

```powershell
git clone https://github.com/IvanMattos89/AI-Career-Agent.git
cd AI-Career-Agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python run.py
```

Para testes e ferramentas de desenvolvimento:

```powershell
pip install -r requirements-dev.txt
python -m pytest -v
```

## Uso principal

1. Importe o currículo em **Meu currículo**.
2. Consulte **Análise IA** para ver a análise salva.
3. Em **Buscar vagas**, selecione Estado/Cidade e busque vagas para o currículo.
4. Compare uma vaga e gere o currículo direcionado em Word ou PDF.
5. Acompanhe as oportunidades na **Central de Carreira**.

## Configuração de IA

Em **Configurações**, escolha Ollama, OpenAI ou modo automático. Caso a IA não responda, a aplicação usa análise local. A Central de Carreira também possui modo local para não bloquear o uso quando não houver provedor disponível.

## Privacidade

- Currículos, análises e histórico são armazenados localmente em `data/`.
- O conteúdo do currículo não deve ser registrado nos logs.
- `.env`, banco SQLite, relatórios e currículos importados são ignorados pelo Git.
- Antes de usar um provedor externo, revise as configurações e os dados que serão enviados.
- Em **Histórico**, a exclusão de currículo remove análises e comparações relacionadas.

## Arquitetura atual

- `app/services/`: importação, análise, busca, matching e relatórios.
- `app/database/`: SQLite, índices e migrações automáticas compatíveis.
- `app/ui/`: páginas PySide6, widgets e workers em segundo plano.
- `app/ai/`: provedores, parser, validação e fallback local.
- `tests/`: testes de parser, interface, fallback, busca e adaptação de currículo.

## Limitações conhecidas

- LinkedIn, Indeed e Gupy podem exigir login ou credenciais de API; a aplicação abre a pesquisa no navegador quando não há integração pública autorizada.
- A busca integrada utiliza fontes públicas e pode variar conforme a disponibilidade das plataformas.
- O currículo direcionado é uma cópia revisável: o usuário deve revisar todos os dados antes de candidatar.

## Histórico de versões

### 3.1

Estabilidade de IA, análise persistida, filtros Brasil, busca na Vagas.com, pipeline, geração de currículo direcionado e importação segura.

### 3.0

Estúdio de candidatura e exportação de materiais.

### 2.0

Central de Carreira, assistente, simulador e plano de ação.

### 1.0

Importação de currículo, análise ATS, Job Match e dashboard.

## Próximos passos

- Conectores estruturados para Greenhouse e Lever.
- Migrações versionadas e modelos normalizados de vagas.
- Consentimento explícito antes do envio a provedores externos.
- Cobertura de testes, lint, CI e empacotamento Windows.

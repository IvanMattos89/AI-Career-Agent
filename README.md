<<<<<<< ours
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
- A OpenAI só é usada após autorização explícita em **Configurações**. Sem consentimento, o app usa Ollama local ou análise local.
- Se o Ollama apontar para outro computador, o envio também exige autorização explícita em **Configurações**.
- Em **Histórico**, a exclusão de currículo remove análises e comparações relacionadas.

### Publicação segura do repositório

Nunca versionar `data/`, `logs/`, arquivos `.env`, relatórios ou currículos importados. Caso algum desses itens já tenha sido enviado ao repositório remoto, removê-lo da branch atual não basta: o histórico remoto deve ser sanitizado com uma ferramenta como `git filter-repo` e o push forçado deve ser realizado somente por quem administra o repositório.

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
=======
# Validador SPED Fiscal (EFD ICMS/IPI)

Programa em Python para validar arquivos texto do **SPED Fiscal / EFD ICMS/IPI** com foco em estrutura de registros, campos de ICMS, CST/CSOSN e conferências básicas de obrigação fiscal.

> Aviso: este projeto não substitui o **PVA EFD ICMS/IPI oficial** nem consultoria fiscal. As regras fiscais mudam por UF, período e operação. Use este validador como pré-validação técnica e sempre confirme a entrega no PVA oficial.

## Base normativa consultada

- Portal SPED da Receita Federal: página de manuais e guias práticos da EFD ICMS/IPI, incluindo leiaute vigente para 2026.
- Portal SPED da Receita Federal: página do PVA/Validador EFD ICMS/IPI.
- CONFAZ: Convênio SINIEF S/N de 1970 e Ajustes SINIEF relacionados ao Código de Situação Tributária (CST) e CSOSN.

## Funcionalidades

- Lê arquivos SPED delimitados por `|`.
- Confere abertura/encerramento obrigatórios (`0000`, `0001`, `0990`, `9990`, `9999`).
- Valida quantidade esperada de campos em registros comuns.
- Valida UF e datas básicas do registro `0000`.
- Valida CST ICMS nacional no formato `ABB`:
  - origem da mercadoria: `0` a `8`;
  - tributação por ICMS: `00`, `10`, `20`, `30`, `40`, `41`, `50`, `51`, `60`, `70`, `90`.
- Identifica CSOSN (`101`, `102`, `103`, `201`, `202`, `203`, `300`, `400`, `500`, `900`) como aviso para conferência de regime.
- Emite avisos de coerência entre CST, alíquota e valor de ICMS em registros analíticos.
- Gera saída em texto ou JSON.

## Instalação para desenvolvimento

```bash
python -m pip install -e .
```

## Uso

```bash
python -m sped_validator.cli caminho/do/sped.txt
```

Saída JSON:

```bash
python -m sped_validator.cli caminho/do/sped.txt --json
```

## Próximos passos recomendados

- Parametrizar regras específicas por UF e período de apuração.
- Expandir o dicionário de registros para todos os blocos da versão vigente do Guia Prático.
- Conferir totais declarados em registros de encerramento por bloco.
- Importar tabelas oficiais atualizadas por versão do leiaute.
>>>>>>> theirs

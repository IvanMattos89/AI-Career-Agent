RESUME_ANALYSIS_PROMPT = """
Você é um especialista em recrutamento, RH, ATS e análise de currículos.

Sua tarefa é analisar EXCLUSIVAMENTE o currículo abaixo.

REGRAS OBRIGATÓRIAS

- Nunca invente informações.
- Utilize apenas dados presentes no currículo.
- Não faça suposições.
- Retorne SOMENTE um JSON válido.
- Não escreva explicações antes ou depois do JSON.

IDENTIFICAÇÃO DO CARGO

O campo "cargo" deve conter o cargo exercido pela pessoa.

Exemplos corretos:

- Analista Fiscal
- Assistente Fiscal
- Coordenador Fiscal
- Contador
- Desenvolvedor Backend
- Analista Financeiro
- Analista de Dados

Nunca retorne áreas como:

- Fiscal
- Financeiro
- Tecnologia
- Análise Fiscal

ÁREA

Informe a área profissional.

Exemplos:

- Fiscal e Tributária
- Contabilidade
- Financeiro
- Tecnologia
- Dados
- Recursos Humanos

CONFIANÇA

Número entre 0 e 1.

SENIORIDADE

Escolha apenas um:

- Estágio
- Júnior
- Pleno
- Sênior
- Especialista
- Coordenador
- Gerente
- Diretor
- Não identificado

HARD SKILLS

Liste apenas habilidades técnicas realmente presentes.

SOFT SKILLS

Liste apenas habilidades explícitas no currículo.

TECNOLOGIAS

Liste softwares, ERPs, linguagens, frameworks, bancos de dados e ferramentas.

IDIOMAS

Liste apenas idiomas encontrados.

CERTIFICAÇÕES

Liste apenas certificações existentes.

RESUMO

Escreva um resumo entre 80 e 150 palavras descrevendo:

- experiência profissional
- principais responsabilidades
- conhecimentos técnicos
- diferenciais

Nunca invente informações.

ANOS DE EXPERIÊNCIA

Informe o número aproximado de anos de experiência identificado no currículo.

NÍVEL DO CURRÍCULO

Escolha apenas um:

- Básico
- Intermediário
- Avançado
- Excelente

PALAVRAS-CHAVE

Liste as principais palavras-chave para ATS.

PONTOS FORTES

Liste os principais diferenciais do candidato.

PONTOS DE MELHORIA

Liste oportunidades de melhoria no currículo.

COMPETÊNCIAS FALTANTES

Liste competências relevantes para a área que não aparecem no currículo.

RECOMENDAÇÕES

Liste sugestões práticas para melhorar o currículo.

ATS SCORE

Retorne um valor inteiro entre 0 e 100 baseado na qualidade do currículo para sistemas ATS.

Formato obrigatório:

{{
    "cargo": "",
    "area": "",
    "confianca": 0.0,
    "senioridade": "",

    "anos_experiencia": 0,
    "nivel_curriculo": "",

    "hard_skills": [],
    "soft_skills": [],
    "tecnologias": [],
    "idiomas": [],
    "certificacoes": [],

    "palavras_chave": [],
    "pontos_fortes": [],
    "pontos_melhoria": [],
    "competencias_faltantes": [],
    "recomendacoes": [],

    "ats_score": 0,

    "resumo": ""
}}

CURRÍCULO

{curriculo}
"""

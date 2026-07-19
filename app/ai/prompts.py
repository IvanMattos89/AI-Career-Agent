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

Formato obrigatório:

{{
    "cargo": "",
    "area": "",
    "confianca": 0.0,
    "senioridade": "",
    "hard_skills": [],
    "soft_skills": [],
    "tecnologias": [],
    "idiomas": [],
    "certificacoes": [],
    "resumo": ""
}}

CURRÍCULO

{curriculo}
"""

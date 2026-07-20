def criar_prompt(contexto):

    return f"""
Você é um especialista em recrutamento, ATS e seleção técnica.

Compare o currículo abaixo com a descrição da vaga.

=========================
CURRÍCULO
=========================

Cargo:
{contexto["cargo"]}

Área:
{contexto["area"]}

Senioridade:
{contexto["senioridade"]}

Hard Skills:
{contexto["hard_skills"]}

Soft Skills:
{contexto["soft_skills"]}

Tecnologias:
{contexto["tecnologias"]}

Idiomas:
{contexto["idiomas"]}

Certificações:
{contexto["certificacoes"]}

Resumo:
{contexto["resumo"]}

=========================
VAGA
=========================

{contexto["vaga"]}

=========================

Retorne EXCLUSIVAMENTE um JSON válido.

Formato obrigatório:

{{
    "compatibilidade": 0,
    "competencias_encontradas": [],
    "competencias_faltantes": [],
    "recomendacoes": [],
    "resumo": ""
}}

Regras:

- compatibilidade deve ser um número de 0 a 100.
- Não escreva explicações fora do JSON.
- Não utilize markdown.
- Não utilize ```json.
- Retorne apenas JSON puro.
"""

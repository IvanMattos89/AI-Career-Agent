import unittest

from app.ai.parser import parse_resume_analysis


class ParserTest(unittest.TestCase):
    def test_parser_accepts_json_fenced(self):
        data = '{"cargo":"Analista","area":"Dados","confianca":2,"senioridade":"Júnior","hard_skills":[],"soft_skills":[],"tecnologias":[],"idiomas":[],"certificacoes":[],"anos_experiencia":-1,"nivel_curriculo":"Básico","palavras_chave":[],"pontos_fortes":[],"pontos_melhoria":[],"competencias_faltantes":[],"recomendacoes":[],"resumo":"texto"}'
        result = parse_resume_analysis(f"```json\n{data}\n```")
        self.assertEqual(result.confianca, 1.0)
        self.assertEqual(result.anos_experiencia, 0)


    def test_parser_rejects_json_list(self):
        with self.assertRaises(ValueError):
            parse_resume_analysis("[]")

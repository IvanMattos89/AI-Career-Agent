import json
import unittest

from app.services.resume_adaptation_service import ResumeAdaptationService


class _Db:
    def obter_analise_ativa(self):
        return {
            "resume_id": 1, "nome_arquivo": "curriculo.docx", "cargo": "Analista Fiscal",
            "area": "Fiscal e Tributária", "senioridade": "Sênior", "anos_experiencia": 10,
            "hard_skills": "Excel; ICMS; SPED", "tecnologias": "ERP; Excel",
        }

    def obter_curriculo(self, _resume_id):
        text = (
            "Maria da Silva\nSão Paulo | maria@example.com\n"
            "EXPERIÊNCIAS PROFISSIONAIS\nEmpresa X | Analista Fiscal | 2016 - Atual\n"
            "- Apuração de ICMS e entrega do SPED com uso de ERP.\n"
            "FORMAÇÃO\nCiências Contábeis - Universidade X\nIDIOMAS\nInglês intermediário"
        )
        from app.services.resume_structure_service import ResumeStructureService
        return {"texto": text, "structured_json": json.dumps(ResumeStructureService.from_text(text))}


class ResumeAdaptationServiceTest(unittest.TestCase):
    def test_prepares_reviewable_resume_without_changing_original(self):
        service = ResumeAdaptationService.__new__(ResumeAdaptationService)
        service.db = _Db()

        resultado = service.preparar("Vaga exige Excel, ICMS e SPED.", "Analista Fiscal")

        self.assertEqual(resultado["vaga"], "Analista Fiscal")
        self.assertIn("ICMS", resultado["competencias_alinhadas"])
        self.assertIn("Empresa X", resultado["texto_original"])
        self.assertTrue(resultado["matriz_evidencias"])
        self.assertIn("antes", resultado["score_ats"])
        self.assertIn("depois", resultado["score_ats"])
        skills = next(
            section for section in resultado["documento"]["sections"]
            if section["key"] == "skills"
        )
        self.assertIn("Tributos", [item["label"] for item in skills["items"]])
        self.assertIn("Sistemas", [item["label"] for item in skills["items"]])
        self.assertNotIn(
            "technologies", [section["key"] for section in resultado["documento"]["sections"]]
        )

    def test_does_not_invent_unproven_requirement(self):
        service = ResumeAdaptationService.__new__(ResumeAdaptationService)
        service.db = _Db()

        result = service.preparar(
            "Requisitos: ICMS, SAP S/4HANA e inglês avançado.",
            "Especialista em Tributos Indiretos",
        )

        matrix = {item["requisito"]: item for item in result["matriz_evidencias"]}
        self.assertEqual(matrix["ICMS"]["status"], "Comprovado")
        self.assertEqual(matrix["SAP S/4HANA"]["status"], "Não comprovado")
        self.assertEqual(matrix["inglês avançado"]["status"], "Não comprovado")
        self.assertNotIn("SAP S/4HANA", result["titulo_direcionado"])

    def test_preserves_every_original_content_line(self):
        service = ResumeAdaptationService.__new__(ResumeAdaptationService)
        service.db = _Db()

        result = service.preparar("Vaga exige ICMS e SPED.", "Analista Fiscal Sênior")
        preview = result["texto_previa"]

        for expected in (
            "Empresa X | Analista Fiscal | 2016 - Atual",
            "Apuração de ICMS e entrega do SPED com uso de ERP.",
            "Ciências Contábeis - Universidade X",
            "Inglês intermediário",
        ):
            self.assertIn(expected, preview)

    def test_changes_positioning_for_distinct_vacancies(self):
        service = ResumeAdaptationService.__new__(ResumeAdaptationService)
        service.db = _Db()

        fiscal = service.preparar("Vaga exige ICMS e SPED.", "Analista Fiscal Sênior")
        sap = service.preparar("Vaga exige SAP S/4HANA e integração fiscal.", "Consultor SAP Fiscal")

        self.assertNotEqual(fiscal["titulo_direcionado"], sap["titulo_direcionado"])
        self.assertNotEqual(fiscal["resumo_direcionado"], sap["resumo_direcionado"])

    def test_groups_specific_competencies_without_losing_tax_items(self):
        groups = ResumeAdaptationService._group_competencies([
            "Tributos", "ICMS", "ICMS-ST", "IPI", "EFD", "EFD ICMS/IPI", "SPED Fiscal",
            "SAP", "SAP S/4HANA", "Excel", "Excel Avançado",
        ])

        self.assertIn("ICMS", groups["Tributos"])
        self.assertIn("ICMS-ST", groups["Tributos"])
        self.assertIn("IPI", groups["Tributos"])
        self.assertIn("EFD ICMS/IPI", groups["Obrigações"])
        self.assertNotIn("EFD", groups["Obrigações"])
        self.assertNotIn("SPED Fiscal", groups["Obrigações"])
        self.assertIn("SAP S/4HANA", groups["Sistemas"])
        self.assertNotIn("SAP", groups["Sistemas"])
        self.assertIn("Excel Avançado", groups["Tecnologia"])

    def test_removes_icons_and_sensitive_header_data(self):
        structure = {
            "header": [
                "Maria da Silva", "📍 São Paulo/SP", "📱 (11) 99999-9999",
                "✉ maria@example.com", "CPF: 123.456.789-00", "Estado civil: casada",
            ],
            "sections": [],
        }

        adapted = ResumeAdaptationService._adapt_structure(
            structure, "Resumo profissional.", "Analista Fiscal", [],
        )
        header = " | ".join(adapted["header"])

        self.assertNotIn("📍", header)
        self.assertNotIn("📱", header)
        self.assertNotIn("✉", header)
        self.assertNotIn("CPF", header)
        self.assertNotIn("Estado civil", header)
        self.assertIn("São Paulo/SP", header)
        self.assertIn("maria@example.com", header)

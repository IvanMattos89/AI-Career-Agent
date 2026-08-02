import unittest

from app.services.resume_structure_service import ResumeStructureService


class ResumeStructureServiceTest(unittest.TestCase):
    def test_recognizes_common_brazilian_section_variants(self):
        text = (
            "Maria da Silva\nContato\nPERFIL PROFISSIONAL\nResumo fiscal\n"
            "EXPERIÊNCIAS PROFISSIONAIS\nEmpresa A\n- Apuração de ICMS\n"
            "FORMAÇÃO\nCiências Contábeis\nCURSOS E CERTIFICAÇÕES\nCurso SPED\n"
            "SISTEMAS\nSAP\nIDIOMAS\nInglês"
        )

        structure = ResumeStructureService.from_text(text)

        self.assertEqual(
            [section["key"] for section in structure["sections"]],
            ["summary", "experience", "education", "courses", "technologies", "languages"],
        )
        rebuilt = ResumeStructureService.to_text(structure)
        for line in ("Resumo fiscal", "Empresa A", "Ciências Contábeis", "Curso SPED", "SAP", "Inglês"):
            self.assertIn(line, rebuilt)

    def test_keeps_unknown_unsectioned_content(self):
        text = "Experiência com ICMS, SPED e ERP."

        structure = ResumeStructureService.from_text(text)

        self.assertEqual(structure["header"], [])
        self.assertEqual(structure["sections"][0]["items"][0]["text"], text)

    def test_preserves_competency_category_labels_in_editable_round_trip(self):
        structure = {
            "header": ["Maria da Silva"],
            "sections": [{
                "key": "skills",
                "title": "COMPETÊNCIAS CENTRAIS",
                "source_title": "",
                "items": [
                    {"text": "ICMS | IPI", "label": "Tributos", "kind": "competency_group"},
                    {
                        "text": "EFD ICMS/IPI | SPED Fiscal",
                        "label": "Obrigações",
                        "kind": "competency_group",
                    },
                    {"text": "SAP S/4HANA", "label": "Sistemas", "kind": "competency_group"},
                    {"text": "Excel Avançado", "label": "Tecnologia", "kind": "competency_group"},
                ],
            }],
        }

        text = ResumeStructureService.to_text(structure)
        rebuilt = ResumeStructureService.from_text(text)
        items = rebuilt["sections"][0]["items"]

        self.assertIn("Tributos: ICMS | IPI", text)
        self.assertIn("Obrigações: EFD ICMS/IPI | SPED Fiscal", text)
        self.assertEqual(
            [item["label"] for item in items],
            ["Tributos", "Obrigações", "Sistemas", "Tecnologia"],
        )


if __name__ == "__main__":
    unittest.main()

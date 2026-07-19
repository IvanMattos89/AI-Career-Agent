from app.ai.skills import SKILLS


class SkillDetector:

    def detectar(self, texto):

        texto_lower = texto.lower()

        encontradas = []

        for categoria in SKILLS.values():

            for skill in categoria:

                if skill.lower() in texto_lower:

                    encontradas.append(skill)

        return sorted(set(encontradas))

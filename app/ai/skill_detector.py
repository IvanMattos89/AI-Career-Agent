import re
import unicodedata

from app.ai.skills import SKILLS


class SkillDetector:
    @staticmethod
    def _normalize(value):
        value = unicodedata.normalize("NFKD", str(value or ""))
        return "".join(char for char in value if not unicodedata.combining(char)).casefold()

    def detectar(self, texto):
        normalized = self._normalize(texto)
        skills = sorted(
            {skill for category in SKILLS.values() for skill in category},
            key=lambda item: (-len(self._normalize(item)), item.casefold()),
        )
        found: list[str] = []
        occupied: list[tuple[int, int]] = []
        for skill in skills:
            term = self._normalize(skill)
            matches = list(re.finditer(r"(?<!\w)" + re.escape(term) + r"(?!\w)", normalized))
            independent = [
                match for match in matches
                if not any(start <= match.start() and match.end() <= end for start, end in occupied)
            ]
            if independent:
                found.append(skill)
                occupied.extend((match.start(), match.end()) for match in independent)
        return sorted(found, key=str.casefold)

from dataclasses import dataclass, field
from typing import List


@dataclass
class ResumeAnalysis:

    cargo: str = ""

    area: str = ""

    confianca: float = 0.0

    senioridade: str = ""

    hard_skills: List[str] = field(default_factory=list)

    soft_skills: List[str] = field(default_factory=list)

    tecnologias: List[str] = field(default_factory=list)

    idiomas: List[str] = field(default_factory=list)

    certificacoes: List[str] = field(default_factory=list)

    resumo: str = ""

    ats_score: int = 0

    sugestoes: List[str] = field(default_factory=list)

    matching: float = 0.0

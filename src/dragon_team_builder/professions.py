"""職業顯示資訊與圖示樣式。"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProfessionInfo:
    color: str
    glyph: str


PROFESSIONS = {
    "刺客": ProfessionInfo("#b33939", "刺"),
    "守衛": ProfessionInfo("#3867d6", "守"),
    "射手": ProfessionInfo("#20bf6b", "射"),
    "戰士": ProfessionInfo("#e67e22", "戰"),
    "法師": ProfessionInfo("#8854d0", "法"),
    "牧師": ProfessionInfo("#f7b731", "牧"),
}


def profession_info(name: str) -> ProfessionInfo | None:
    return PROFESSIONS.get(name)

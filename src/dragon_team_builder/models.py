"""角色資料模型。"""

from dataclasses import dataclass, field
from typing import Literal


SourceKind = Literal["guide", "official", "community", "unknown"]


@dataclass(slots=True)
class SourceReference:
    """單筆資料的來源與可信度。"""

    kind: SourceKind
    title: str
    url: str
    accessed_at: str
    confidence: Literal["high", "medium", "low"] = "medium"


@dataclass(slots=True)
class Skill:
    """角色的一項技能。"""

    name: str
    description: str
    skill_type: str = ""
    tags: list[str] = field(default_factory=list)
    metrics: list[str] = field(default_factory=list)
    sources: list[SourceReference] = field(default_factory=list)


@dataclass(slots=True)
class Character:
    """可供瀏覽與組隊篩選的角色資料。"""

    id: str
    name: str
    class_name: str
    main_faction: str
    secondary_faction: str
    skills: list[Skill] = field(default_factory=list)
    special_functions: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)
    image_url: str = ""
    image_file: str = ""
    quality: str = ""
    tier: str = ""
    guide_notes: str = ""
    source: SourceReference | None = None

    @property
    def factions(self) -> list[str]:
        """回傳去除空值與重複後的陣營。"""

        return list(dict.fromkeys(
            faction
            for faction in (self.main_faction, self.secondary_faction)
            if faction
        ))

    @property
    def skill_tags(self) -> list[str]:
        """回傳技能標籤，供篩選器建立選項。"""

        return list(dict.fromkeys(
            tag
            for skill in self.skills
            for tag in skill.tags
            if tag
        ))

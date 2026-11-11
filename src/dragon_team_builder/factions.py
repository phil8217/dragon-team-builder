"""台服顯示用陣營資訊。"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FactionInfo:
    key: str
    name: str
    color: str
    image_file: str
    description: str


FACTIONS = {
    "元素": FactionInfo(
        "elemental_echo",
        "元素迴響",
        "#e67e22",
        "data/factions/elemental_echo.webp",
        "擅長元素狀態與元素反應。",
    ),
    "曠野": FactionInfo(
        "wild_spirit",
        "曠野之靈",
        "#27ae60",
        "data/factions/wild_spirit.webp",
        "偏向持續戰鬥、怒氣與野性效果。",
    ),
    "奧術": FactionInfo(
        "arcane_wisdom",
        "奧術智慧",
        "#2980b9",
        "data/factions/arcane_wisdom.webp",
        "偏向奧義、法術與能量循環。",
    ),
    "聖堂": FactionInfo(
        "sanctum_glory",
        "聖堂榮光",
        "#f1c40f",
        "data/factions/sanctum_glory.webp",
        "偏向祝福、保護與神聖效果。",
    ),
    "彼岸": FactionInfo(
        "otherworld_return",
        "彼岸再臨",
        "#22c55e",
        "data/factions/otherworld_return.webp",
        "偏向遺言、死亡與再臨效果。",
    ),
    "幻境": FactionInfo(
        "illusion_veil",
        "幻境秘影",
        "#9b59b6",
        "data/factions/illusion_veil.webp",
        "偏向控制、幻影與特殊狀態。",
    ),
}


def faction_info(name: str) -> FactionInfo | None:
    return FACTIONS.get(name)

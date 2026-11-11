"""合併 Dragon Companion 技能頁與攻略角色資料。"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from dragon_team_builder.quality import is_legendary_or_higher, normalize_quality


ROOT = Path(__file__).resolve().parents[1]
CHARACTER_DATA = ROOT / "src" / "dragon_team_builder" / "data" / "characters.json"
PAGES = ROOT / "data" / "dragoncompanion"
OUTPUT = CHARACTER_DATA
SOURCE_URL = "https://www.dragoncompanion.com/zh-Hant/characters/"
SITE_URL = "https://www.dragoncompanion.com"
CLASS_NORMALIZATION = {
    "守護者": "守衛",
    "弓手": "射手",
    "牧師": "牧師",
}
PAGE_NAME_ALIASES = {
    "gamekee-kasumi": "霞",
    "gamekee-galahad": "加拉哈德",
    "gamekee-gaia": "蓋亞",
    "caesar_ssr_plus": "凱撤",
    "helveil_ssr_plus": "赫爾維爾",
    "heidrun_ssr_plus": "海德輪",
    "goren_ssr": "戈輪",
    "gamekee-dartagnan": "達達尼昂",
    "ifrit_ssr_plus": "依芙利特",
    "gamekee-marie-rose": "瑪莉•蘿絲",
    "tyrfing_ssr_plus": "提爾鋒",
    "hercules_ssr_ex": "海克力斯",
    "cerberus_ssr": "刻爾柏洛斯",
    "poseidon_ssr_ex": "波賽頓",
    "arachne_ssr_plus": "阿拉克涅",
    "gamekee-quetzal": "魁劄爾",
    "gamekee-hypnos": "修普諾斯",
    "gamekee-honoka": "穗香",
    "ophelia_ssr_plus": "奧菲利亞",
    "siren_sr": "塞任",
}

TAG_PATTERNS = {
    "擊倒": "擊倒",
    "沉默": "沉默",
    "免死": "免死",
    "護盾": "護盾",
    "治療": "治療",
    "增傷": "增傷",
    "減傷": "減傷",
    "驅散": "驅散",
    "召喚": "召喚",
    "分身": "分身",
    "冰凍": "冰凍",
    "麻痺": "麻痺",
    "石化": "石化",
    "嘲諷": "嘲諷",
    "無敵": "無敵",
    "復活": "復活",
    "放逐": "放逐",
    "禁療": "禁療",
    "減速": "減速",
    "灼燒": "灼燒",
    "中毒": "中毒",
    "流血": "流血",
    "暴擊": "暴擊",
    "真傷": "真實傷害",
    "回復": "回復",
    "回能": "回復奧義",
    "減費": "減少消耗",
    "加費": "增加消耗",
    "降攻": "降低攻擊",
    "降防": "降低防禦",
    "降療": "降低治療",
    "降CD": "降低冷卻",
}
SKILL_TYPE_NAMES = {
    "Overdrive": "奧義",
    "Ultimate Skill": "絕技",
    "Secret Skill": "秘技",
    "Special Skill": "特技",
    "Passive Skill": "天賦",
    "Talent": "天賦",
}


def compact(value: str) -> str:
    return re.sub(r"[\s·•・,，:：()（）《》「」【】]", "", value).lower()


def normalize_functions(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        for item in re.split(r"[、，,/]+", value):
            item = item.strip().strip("?")
            if item and item not in {"其他陣營", "定位", "神格"}:
                result.append(item)
    return list(dict.fromkeys(result))


def text_from_markup(value: str) -> str:
    value = re.sub(r"<br\s*/?>", "\n", value, flags=re.I)
    value = re.sub(r"<[^>]+>", "", value)
    return html.unescape(value).strip()


def first(pattern: str, content: str, flags: int = re.S) -> str:
    match = re.search(pattern, content, flags)
    return text_from_markup(match.group(1)) if match else ""


def all_matches(pattern: str, content: str, flags: int = re.S) -> list[str]:
    return [text_from_markup(value) for value in re.findall(pattern, content, flags)]


def parse_page(path: Path) -> dict:
    content = path.read_text(encoding="utf-8")
    overview = first(r'<div class="detail-heading".*?<h1>(.*?)</h1>', content)
    epithet = first(r'<div class="detail-heading".*?<h1>.*?</h1><p>(.*?)</p>', content)
    profession = first(r'<div class="fact"><dt>職業</dt><dd>(.*?)</dd>', content)
    image_path = first(
        r'<img class="detail-portrait"[^>]+src="([^"]+)"',
        content,
        flags=re.S,
    )
    image_url = (
        SITE_URL + image_path
        if image_path.startswith("/")
        else image_path
    )
    heading = first(r'<div class="detail-heading">(.*?)</header>', content)
    factions = [
        text_from_markup(value)
        for value in re.findall(
            r'<span class="badge faction-badge"[^>]*>.*?</span>', heading, re.S
        )
    ]
    skill_cards = re.findall(
        r'<article class="skill-card">(.*?)(?=</article>)', content, re.S
    )
    skills: list[dict] = []
    for card in skill_cards:
        name = first(r"<h3>(.*?)</h3>", card)
        if not name:
            continue
        skill_type = first(r'<span class="badge[^"]*">(.*?)</span>', card)
        skill_type = SKILL_TYPE_NAMES.get(skill_type, skill_type)
        metrics = all_matches(r'<div class="skill-metrics">(.*?)</div>', card)
        description = first(r"<p>(.*?)</p>", card)
        tags = [label for token, label in TAG_PATTERNS.items() if token in description]
        skills.append(
            {
                "name": name,
                "description": description,
                "skill_type": skill_type,
                "tags": tags,
                "sources": [
                    {
                        "kind": "community",
                        "title": "Dragon Companion 角色技能頁",
                        "url": SOURCE_URL + path.name,
                        "accessed_at": "2026-11-11",
                        "confidence": "medium",
                    }
                ],
                "metrics": metrics,
            }
        )
    talent_name = first(
        r'<div class="talent-title">.*?<h3>(.*?)</h3>',
        content,
    )
    talent_levels = all_matches(
        r'<div class="talent-level-effect">(.*?)</div>',
        content,
    )
    if talent_name and talent_levels:
        skills.append(
            {
                "name": talent_name,
                "description": "\n".join(talent_levels),
                "skill_type": "天賦",
                "tags": [
                    label
                    for token, label in TAG_PATTERNS.items()
                    if any(token in level for level in talent_levels)
                ],
                "metrics": [],
                "sources": [
                    {
                        "kind": "community",
                        "title": "Dragon Companion 角色技能頁",
                        "url": SOURCE_URL + path.name,
                        "accessed_at": "2026-11-11",
                        "confidence": "medium",
                    }
                ],
            }
        )
    return {
        "page_name": overview,
        "epithet": epithet,
        "profession": profession,
        "image_url": image_url,
        "factions": factions,
        "skills": skills,
        "url": SOURCE_URL + path.name,
    }


def find_guide_record(records: list[dict], page: dict) -> dict | None:
    page_name = compact(page["page_name"])
    page_epithet = compact(page["epithet"])
    candidates = []
    for record in records:
        guide_name = compact(record["name"])
        if page_name and page_name in guide_name:
            candidates.append(record)
    if len(candidates) == 1:
        return candidates[0]
    for record in candidates:
        if page_epithet and page_epithet in compact(record["name"]):
            return record
    return None


def new_record(page: dict, path: Path) -> dict:
    factions = page["factions"] + [""] * 2
    class_name = page["profession"] or "未分類"
    return {
        "id": "current-" + path.stem,
        "name": " • ".join(
            value for value in (page["epithet"], page["page_name"]) if value
        ),
        "class_name": class_name,
        "main_faction": factions[0],
        "secondary_faction": factions[1],
        "skills": [],
        "special_functions": [],
        "aliases": [page["page_name"]] if page["epithet"] else [],
        "image_url": page["image_url"],
        "quality": "",
        "tier": "",
        "guide_notes": "",
        "source": {
            "kind": "community",
            "title": "Dragon Companion 角色頁",
            "url": page["url"],
            "accessed_at": "2026-11-11",
            "confidence": "medium",
        },
    }


def main() -> None:
    records = json.loads(CHARACTER_DATA.read_text(encoding="utf-8"))
    pages = [parse_page(path) | {"path": path} for path in sorted(PAGES.glob("*.html"))]
    matched = 0
    added = 0
    for page in pages:
        alias = PAGE_NAME_ALIASES.get(page["path"].stem, "")
        record = find_guide_record(records, page)
        if record is None and alias:
            record = next(
                (
                    candidate
                    for candidate in records
                    if alias in candidate["name"]
                ),
                None,
            )
        if record is None:
            record = new_record(page, page["path"])
            records.append(record)
            added += 1
        else:
            matched += 1
        record["skills"] = page["skills"]
        record["image_url"] = page["image_url"] or record.get("image_url", "")
        record["special_functions"] = normalize_functions(
            record["special_functions"] + [
                tag
                for skill in page["skills"]
                for tag in skill["tags"]
            ]
        )
        if not record["main_faction"]:
            record["main_faction"] = page["factions"][0] if page["factions"] else ""
        if not record["secondary_faction"] and len(page["factions"]) > 1:
            record["secondary_faction"] = page["factions"][1]
        record.setdefault("source", {})
        record["class_name"] = CLASS_NORMALIZATION.get(
            record["class_name"], record["class_name"]
        )
        record["quality"] = normalize_quality(record.get("quality", ""))

    by_base_id = {
        record["id"]: record
        for record in records
        if record["skills"] and not record["id"].endswith("-專武")
    }
    for record in records:
        if record["skills"] or not record["id"].endswith("-專武"):
            continue
        base = by_base_id.get(record["id"][:-3])
        if base:
            record["skills"] = base["skills"]
            record["special_functions"] = list(
                dict.fromkeys(
                    record["special_functions"] + base["special_functions"]
                )
            )

    records = [
        record for record in records
        if is_legendary_or_higher(record.get("quality", ""))
    ]
    records.sort(key=lambda item: (item["class_name"], item["name"]))
    OUTPUT.write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    skill_count = sum(len(record["skills"]) for record in records)
    print(f"已合併 {matched} 筆攻略角色、加入 {added} 筆目前角色")
    print(f"角色總數：{len(records)}，技能總數：{skill_count}")


if __name__ == "__main__":
    main()

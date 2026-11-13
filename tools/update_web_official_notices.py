"""更新 GitHub Pages 使用的台服官方公告清單。"""

from __future__ import annotations

import json
import hashlib
import os
import re
import sys
import tempfile
import urllib.request
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dragon_team_builder.official_updates import (
    _fetch,
    _new_character_names,
    _notice_date,
    _skill_blocks,
    _visible_text,
    apply_official_updates,
    check_official_updates,
)


WEB_CHARACTER_DATA = ROOT / "web" / "data" / "characters.json"
WEB_VERSION_DATA = ROOT / "web" / "data" / "data_version.json"
WEB_NOTICE_DATA = ROOT / "web" / "data" / "official_maintenance_notices.json"
WEB_IMAGE_DIR = ROOT / "web" / "data" / "images"
CLASS_NAMES = ("守衛", "牧師", "刺客", "戰士", "射手", "法師")
FACTION_NAMES = {
    "曠野之靈": "曠野",
    "聖堂榮光": "聖堂",
    "彼岸再臨": "彼岸",
    "幻境秘影": "幻境",
    "元素迴響": "元素",
    "奧術智慧": "奧術",
}
CLASS_PREFIXES = {
    "守衛": "guardian",
    "牧師": "support",
    "刺客": "assassin",
    "戰士": "warrior",
    "射手": "ranger",
    "法師": "mage",
}
OFFICIAL_TRANSLATION_NAMES = {
    "戀歌謬斯•艾拉托": "戀歌謬斯•艾拉託",
    "小惡魔女僕•瑪莉•蘿絲": "小惡魔女僕•瑪莉•蘿絲",
    "英靈統領•海德倫": "英魂統領•海德輪",
    "大力神•赫拉克勒斯": "大力神•海克力斯",
    "黑貓女神•克里奧佩特拉": "埃及豔後•克里奧佩特拉",
    "凱旋皇女•凱撒": "凱旋皇女•凱撤",
    "霜星獵手•俄里翁": "雙星獵手•俄裏翁",
    "聖劍主教•奧菲莉亞": "聖劍主教•奧菲利亞",
    "噬血魔劍•提爾鋒": "嗜血魔劍•提爾鋒",
    "大天使．加百列": "大天使•加百列",
    "愛神．維納斯": "愛神•維納斯",
    "墮落女武神．赫爾薇爾": "墮落女武神•赫爾維爾",
}


def atomic_write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as temporary:
        temporary.write(content)
        temporary_path = Path(temporary.name)
    try:
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def download_character_image(record: dict) -> str:
    url = record.get("image_url", "")
    if not url:
        return ""
    extension = ".jpg" if ".jpg" in url.lower() else ".webp"
    filename = hashlib.sha256(record["id"].encode("utf-8")).hexdigest()[:16] + extension
    target = WEB_IMAGE_DIR / filename
    if not target.exists():
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "DragonTeamBuilder/0.1"},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(response.read())
    return f"data/images/{target.name}"


def load_existing_notices() -> dict:
    if not WEB_NOTICE_DATA.exists():
        return {}
    payload = json.loads(WEB_NOTICE_DATA.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("網頁版公告資料必須是 JSON 物件。")
    return payload


def normalized_name(name: str) -> str:
    return re.sub(r"\s+", " ", name.replace("‧", " • ").replace("・", " • ").replace("．", " • ")).strip()


def comparison_name(name: str) -> str:
    return re.sub(r"\s*•\s*", "•", normalized_name(name))


def existing_character_names(character: dict) -> set[str]:
    name = normalized_name(character.get("name", ""))
    aliases = {normalized_name(alias) for alias in character.get("aliases", [])}
    aliases.discard("")
    return {name, *aliases} - {""}


def merge_translation_duplicates(records: list[dict]) -> bool:
    changed = False
    for official_name, existing_name in OFFICIAL_TRANSLATION_NAMES.items():
        official_key = comparison_name(official_name)
        existing_key = comparison_name(existing_name)
        canonical = next(
            (
                record for record in records
                if comparison_name(record.get("name", "")) == existing_key
            ),
            None,
        )
        duplicate = next(
            (
                record for record in records
                if comparison_name(record.get("name", "")) == official_key
                and record is not canonical
            ),
            None,
        )
        if not canonical or not duplicate:
            continue
        aliases = list(canonical.get("aliases", []))
        for value in [duplicate.get("name", ""), *duplicate.get("aliases", [])]:
            if value and value != canonical.get("name") and value not in aliases:
                aliases.append(value)
        if canonical.get("name") != official_name:
            aliases.append(canonical["name"])
            canonical["name"] = official_name
        canonical["aliases"] = aliases
        records.remove(duplicate)
        changed = True
    return changed


def apply_official_translation_name(name: str, records: list[dict]) -> bool:
    target_name = next(
        (
            target
            for official, target in OFFICIAL_TRANSLATION_NAMES.items()
            if comparison_name(official) == comparison_name(name)
        ),
        None,
    )
    if not target_name:
        return False
    canonical = next(
        (
            record for record in records
            if comparison_name(record.get("name", "")) in {
                comparison_name(name),
                comparison_name(target_name),
            }
        ),
        None,
    )
    if not canonical:
        return False
    if canonical.get("name") != name:
        aliases = list(canonical.get("aliases", []))
        if canonical.get("name") and canonical["name"] not in aliases:
            aliases.append(canonical["name"])
        canonical["name"] = name
        canonical["aliases"] = aliases
    return True


def character_id(name: str, class_name: str, records: list[dict]) -> str:
    prefix = CLASS_PREFIXES.get(class_name, "unknown")
    base = f"{prefix}-{normalized_name(name).replace(' • ', '-')}"
    candidate = base
    suffix = 2
    used = {record.get("id") for record in records}
    while candidate in used:
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate


def extract_quality(lines: list[str], marker: int) -> str:
    for index in range(marker + 1, min(marker + 30, len(lines))):
        line = lines[index]
        if not line.startswith("品質："):
            continue
        value = line.split("：", 1)[1].strip()
        if value:
            return value
        for following in lines[index + 1:]:
            if following.strip():
                return following.strip()
    return "未知"


def first_image_after_quality(content: str, raw_name: str, notice_url: str) -> str:
    name_position = content.find(raw_name)
    if name_position < 0:
        return ""
    quality_position = content.find("品質", name_position)
    if quality_position < 0:
        return ""
    image_match = re.search(
        r"<img[^>]+src=[\"']([^\"']+)",
        content[quality_position:],
        flags=re.S,
    )
    return urljoin(notice_url, image_match.group(1)) if image_match else ""


def new_character_from_notice(
    content: str,
    url: str,
    records: list[dict],
) -> list[dict]:
    text = _visible_text(content)
    lines = text.splitlines()
    names = _new_character_names(text)
    created = []
    for raw_name in names:
        name = normalized_name(raw_name)
        if apply_official_translation_name(name, records + created):
            continue
        if any(name in existing_character_names(record) for record in records + created):
            continue
        marker = next(
            (index for index, line in enumerate(lines) if raw_name in line),
            None,
        )
        if marker is None:
            continue
        block = lines[marker:marker + 14]
        quality = extract_quality(lines, marker)
        class_name = next(
            (value for value in CLASS_NAMES if any(line == f"職業：{value}" for line in block)),
            "未分類",
        )
        factions = next(
            (
                [FACTION_NAMES.get(value.strip(), value.strip()) for value in line.split("：", 1)[1].split("、")]
                for line in block
                if line.startswith("陣營：")
            ),
            [],
        )
        special = []
        if marker + 1 < len(lines) and "：" not in lines[marker + 1]:
            special = [item for item in lines[marker + 1].split() if item]
        source = {
            "kind": "official",
            "title": f"台服官方公告：{_notice_date(url)} 維護更新",
            "url": url,
            "accessed_at": datetime.now(ZoneInfo("Asia/Taipei")).date().isoformat(),
            "confidence": "medium",
        }
        image_url = first_image_after_quality(content, raw_name, url)
        skills = [
            {
                "name": skill_name,
                "description": description,
                "skill_type": skill_type,
                "tags": list(special),
                "metrics": [],
                "sources": [source],
            }
            for skill_type, skill_name, description in _skill_blocks(text)
        ]
        aliases = [
            part.strip()
            for part in re.split(r"\s*•\s*", name)
            if part.strip() and part.strip() != name
        ]
        record = {
                "id": character_id(name, class_name, records + created),
                "name": name,
                "class_name": class_name,
                "main_faction": factions[0] if factions else "未分類",
                "secondary_faction": factions[1] if len(factions) > 1 else "",
                "skills": skills,
                "special_functions": list(special),
                "aliases": aliases,
                "image_url": image_url,
                "quality": quality,
                "tier": "",
                "guide_notes": f"台服 {source['accessed_at']} 官方公告新增角色。",
                "source": source,
                "official_updates": [],
            }
        record["image_file"] = download_character_image(record)
        created.append(record)
    return created


def main() -> None:
    characters = json.loads(WEB_CHARACTER_DATA.read_text(encoding="utf-8-sig"))
    if not isinstance(characters, list):
        raise ValueError("角色資料必須是 JSON 陣列。")
    characters_changed = merge_translation_duplicates(characters)

    existing = load_existing_notices()
    with tempfile.TemporaryDirectory() as temporary_directory:
        temporary_path = Path(temporary_directory)
        old_index = {
            "notices": existing.get("notices", []),
        }
        (temporary_path / "notice_index.json").write_text(
            json.dumps(old_index, ensure_ascii=False),
            encoding="utf-8",
        )
        report = check_official_updates(characters, temporary_path)

    changed_urls = [
        notice["url"]
        for notice in report.get("changed_notices", [])
        if notice.get("url")
    ]
    if changed_urls:
        with tempfile.TemporaryDirectory() as backup_directory:
            apply_official_updates(
                characters,
                changed_urls,
                WEB_CHARACTER_DATA,
                WEB_VERSION_DATA,
                backup_directory,
            )
        characters = json.loads(WEB_CHARACTER_DATA.read_text(encoding="utf-8-sig"))
    created = []
    for notice in report.get("changed_notices", []):
        if not notice.get("new_characters"):
            continue
        content = _fetch(notice["url"])
        created.extend(new_character_from_notice(content, notice["url"], characters + created))
    if created or characters_changed:
        characters.extend(created)
        atomic_write_json(WEB_CHARACTER_DATA, characters)
        version = json.loads(WEB_VERSION_DATA.read_text(encoding="utf-8"))
        version.update({
            "version": datetime.now(ZoneInfo("Asia/Taipei")).date().isoformat(),
            "updated_at": datetime.now(ZoneInfo("Asia/Taipei")).date().isoformat(),
            "character_count": len(characters),
        })
        atomic_write_json(WEB_VERSION_DATA, version)
    notices = report.get("notices", [])
    payload = {
        "source": "https://sod.game-beans.com/jx/sodNotice/index.html",
        "accessed_at": report.get("checked_at", ""),
        "last_checked_at": datetime.now(
            ZoneInfo("Asia/Taipei")
        ).strftime("%Y-%m-%d %H:%M:%S"),
        "index_pages": 2,
        "notice_count": len(notices),
        "notices": notices,
    }
    atomic_write_json(WEB_NOTICE_DATA, payload)
    print(
        f"官方公告檢查完成：{len(notices)} 筆公告，"
        f"本次變更 {len(report.get('changed_notices', []))} 筆，"
        f"自動新增角色 {len(created)} 名。"
    )


if __name__ == "__main__":
    main()

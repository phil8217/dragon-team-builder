"""從 GameKee 角色頁補充中文技能與天賦資料。"""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from difflib import SequenceMatcher
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHARACTER_DATA = ROOT / "src" / "dragon_team_builder" / "data" / "characters.json"
BASE_URL = "https://www.gamekee.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "X-Requested-With": "XMLHttpRequest",
    "game-alias": "lhlr",
    "Lang": "zh-cn",
    "Referer": "https://www.gamekee.com/lhlr/",
}
TYPE_NAMES = {
    "天赋": "天賦",
    "奥义": "奧義",
    "绝技": "絕技",
    "秘技": "秘技",
    "特技": "特技",
}


def get_json(url: str) -> dict:
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read())


def compact(value: str) -> str:
    return re.sub(r"[\s·•・,，:：()（）《》「」【】\-]", "", value).lower()


def editor_text(value: object) -> str:
    if isinstance(value, dict):
        if isinstance(value.get("text"), str):
            return value["text"]
        return "".join(editor_text(item) for item in value.values())
    if isinstance(value, list):
        return "".join(editor_text(item) for item in value)
    return ""


def find_skill_info(value: object) -> list[dict]:
    if isinstance(value, dict):
        if value.get("type") == "skill-info":
            return value.get("data", {}).get("skillList", [])
        for child in value.values():
            result = find_skill_info(child)
            if result:
                return result
    elif isinstance(value, list):
        for child in value:
            result = find_skill_info(child)
            if result:
                return result
    return []


def parse_skills(content_json: str) -> list[dict]:
    try:
        content = json.loads(content_json)
    except json.JSONDecodeError:
        return []
    skills = []
    for item in find_skill_info(content):
        name = editor_text(item.get("name")).strip()
        description = editor_text(item.get("desc")).strip()
        match = re.match(r"([^：:]+)[：:]\s*(.*)", name)
        if not match or not description:
            continue
        skill_type = TYPE_NAMES.get(match.group(1).strip())
        if not skill_type:
            continue
        skills.append(
            {
                "name": match.group(2).strip(),
                "description": description,
                "skill_type": skill_type,
                "tags": [],
                "metrics": [],
                "sources": [
                    {
                        "kind": "community",
                        "title": "GameKee《龍魂旅人》角色資料",
                        "url": "https://www.gamekee.com/lhlr/",
                        "accessed_at": "2026-11-11",
                        "confidence": "medium",
                    }
                ],
            }
        )
    return skills


def fetch_detail(item: dict) -> tuple[dict, list[dict]]:
    try:
        detail = get_json(f"{BASE_URL}/v1/content/detail/{item['id']}")["data"]
        skills = parse_skills(detail.get("content_json", ""))
        source_url = f"{BASE_URL}/lhlr/{item['id']}.html"
        for skill in skills:
            skill["sources"][0]["url"] = source_url
        return detail, skills
    except (OSError, KeyError, TypeError, json.JSONDecodeError):
        return item, []


def match_record(title: str, records: list[dict]) -> dict | None:
    title_key = compact(title)
    def values_for(record: dict) -> list[str]:
        values = [record["name"], *record.get("aliases", [])]
        return [
            part
            for value in values
            for part in re.split(r"[•・·]", value)
            if part.strip()
        ]

    exact = [
        record
        for record in records
        if any(
            title_key in compact(value) or compact(value) in title_key
            for value in values_for(record)
        )
    ]
    if len(exact) == 1:
        return exact[0]

    scored = sorted(
        (
            (
                max(
                    SequenceMatcher(None, title_key, compact(value)).ratio()
                    for value in values_for(record)
                    if value
                ),
                record,
            )
            for record in records
        ),
        key=lambda item: item[0],
        reverse=True,
    )
    if scored and scored[0][0] >= 0.72:
        if len(scored) == 1 or scored[0][0] - scored[1][0] >= 0.08:
            return scored[0][1]
    return None


def main() -> None:
    records = json.loads(CHARACTER_DATA.read_text(encoding="utf-8"))
    items = []
    for page in range(1, 6):
        query = urllib.parse.urlencode(
            {"alias": "lhlr", "game-alias": "lhlr", "page_no": page, "limit": 100}
        )
        items.extend(get_json(f"{BASE_URL}/v1/content/pageList?{query}")["data"])
    items = [item for item in items if item.get("type") == 4]
    with ThreadPoolExecutor(max_workers=12) as pool:
        details = list(pool.map(fetch_detail, items))

    updated = 0
    added_talents = 0
    for detail, skills in details:
        if not skills:
            continue
        record = match_record(detail.get("title", ""), records)
        if record is None:
            continue
        by_type = {skill["skill_type"]: skill for skill in skills}
        merged = []
        seen_types: set[str] = set()
        for skill in record["skills"]:
            replacement = by_type.get(skill["skill_type"])
            if replacement:
                merged.append(replacement)
                seen_types.add(skill["skill_type"])
            else:
                merged.append(skill)
        for skill in skills:
            if skill["skill_type"] not in seen_types and not any(
                item["skill_type"] == skill["skill_type"] for item in merged
            ):
                merged.append(skill)
                if skill["skill_type"] == "天賦":
                    added_talents += 1
        if merged != record["skills"]:
            record["skills"] = merged
            updated += 1

    CHARACTER_DATA.write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"更新角色：{updated}；補入天賦：{added_talents}")


if __name__ == "__main__":
    main()

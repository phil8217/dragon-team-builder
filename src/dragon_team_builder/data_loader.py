"""讀取角色 JSON 資料。"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .abilities import normalize_abilities
from .models import Character, Skill, SourceReference
from .quality import normalize_quality
from .text_normalizer import to_traditional


def _source(value: dict | None) -> SourceReference | None:
    if value is None:
        return None
    source = dict(value)
    source["title"] = to_traditional(source.get("title", ""))
    return SourceReference(**source)


def load_characters(path: str | Path) -> list[Character]:
    """從 JSON 載入角色資料；格式錯誤時直接拋出明確例外。"""

    source_path = Path(path)
    with source_path.open(encoding="utf-8") as file:
        records = json.load(file)

    if not isinstance(records, list):
        raise ValueError(f"角色資料必須是陣列：{source_path}")

    characters: list[Character] = []
    for record in records:
        if not isinstance(record, dict):
            raise ValueError(f"角色資料項目必須是物件：{source_path}")
        record = dict(record)
        for key in (
            "name",
            "class_name",
            "main_faction",
            "secondary_faction",
            "quality",
            "tier",
            "guide_notes",
        ):
            record[key] = to_traditional(record.get(key, ""))
        record["special_functions"] = normalize_abilities([
            to_traditional(value)
            for value in record.get("special_functions", [])
        ])
        record["aliases"] = [
            to_traditional(value) for value in record.get("aliases", [])
        ]
        record.setdefault("image_url", "")
        record.setdefault("image_file", "")
        record["quality"] = normalize_quality(record.get("quality", ""))
        record["source"] = _source(record.get("source"))
        record["skills"] = [
            Skill(
                **{
                    **skill,
                    "name": to_traditional(skill.get("name", "")),
                    "description": to_traditional(
                        skill.get("description", "")
                    ),
                    "skill_type": to_traditional(skill.get("skill_type", "")),
                    "tags": normalize_abilities([
                        to_traditional(tag)
                        for tag in skill.get("tags", [])
                    ]),
                    "metrics": [
                        to_traditional(metric)
                        for metric in skill.get("metrics", [])
                    ],
                    "sources": [
                        _source(source)
                        for source in skill.get("sources", [])
                    ],
                }
            )
            for skill in record.get("skills", [])
        ]
        characters.append(Character(**record))
    return characters


def character_to_dict(character: Character) -> dict:
    """將角色轉換成可序列化的字典。"""

    return asdict(character)

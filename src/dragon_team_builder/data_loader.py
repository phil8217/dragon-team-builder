"""讀取角色 JSON 資料。"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .abilities import classify_abilities
from .mechanics import MECHANICS
from .models import Character, Skill, SourceReference
from .quality import normalize_quality
from .text_normalizer import to_traditional


def _as_list(value: object) -> list:
    """將更新資料中的單值或空值安全轉成清單。"""

    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def _source(value: dict | None) -> SourceReference | None:
    if value is None:
        return None
    source = dict(value)
    source["title"] = to_traditional(source.get("title", ""))
    return SourceReference(**source)


def load_characters(path: str | Path) -> list[Character]:
    """從 JSON 載入角色資料；格式錯誤時直接拋出明確例外。"""

    source_path = Path(path)
    with source_path.open(encoding="utf-8-sig") as file:
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
        original_functions = [
            to_traditional(value)
            for value in _as_list(record.get("special_functions"))
            if isinstance(value, str)
        ]
        record["aliases"] = [
            to_traditional(value)
            for value in _as_list(record.get("aliases"))
            if isinstance(value, str)
        ]
        record.setdefault("image_url", "")
        record.setdefault("image_file", "")
        record.setdefault("official_updates", [])
        record["quality"] = normalize_quality(record.get("quality", ""))
        record["source"] = _source(record.get("source"))
        loaded_skills = [
            Skill(
                **{
                    **skill,
                    "name": to_traditional(skill.get("name", "")),
                    "description": to_traditional(
                        skill.get("description", "")
                    ),
                    "skill_type": to_traditional(skill.get("skill_type", "")),
                    "tags": classify_abilities(
                        [to_traditional(skill.get("name", ""))],
                        to_traditional(skill.get("description", "")),
                    ),
                    "metrics": [
                        to_traditional(metric)
                        for metric in _as_list(skill.get("metrics"))
                        if isinstance(metric, str)
                    ],
                    "sources": [
                        _source(source)
                        for source in _as_list(skill.get("sources"))
                        if isinstance(source, dict)
                    ],
                }
            )
            for skill in _as_list(record.get("skills"))
            if isinstance(skill, dict)
        ]
        record["skills"] = loaded_skills
        classified_functions: list[str] = []
        all_descriptions = " ".join(
            skill.description for skill in loaded_skills
        )
        for value in original_functions:
            if (
                value in MECHANICS
                and value in all_descriptions
                and value not in classified_functions
            ):
                classified_functions.append(value)
        for tag in (tag for skill in loaded_skills for tag in skill.tags):
            if tag not in classified_functions:
                classified_functions.append(tag)
        record["special_functions"] = list(dict.fromkeys(classified_functions))
        characters.append(Character(**record))
    return characters


def character_to_dict(character: Character) -> dict:
    """將角色轉換成可序列化的字典。"""

    return asdict(character)

"""讀取角色 JSON 資料。"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .models import Character, Skill, SourceReference


def _source(value: dict | None) -> SourceReference | None:
    if value is None:
        return None
    return SourceReference(**value)


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
        record.setdefault("image_url", "")
        record.setdefault("image_file", "")
        record["source"] = _source(record.get("source"))
        record["skills"] = [
            Skill(
                **{
                    **skill,
                    "sources": [
                        SourceReference(**source)
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

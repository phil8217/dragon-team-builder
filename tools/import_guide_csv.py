"""將攻略 Google 試算表的職業 CSV 匯入角色 JSON。

此工具只匯入攻略已提供的資料；技能文字由後續具名來源逐筆補入。
"""

from __future__ import annotations

import csv
import json
import json
import re
import sys
from datetime import date
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from dragon_team_builder.quality import is_legendary_or_higher, normalize_quality


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
OUTPUT = ROOT / "src" / "dragon_team_builder" / "data" / "characters.json"
SHEET_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1BtV2fdlYPytwNG4lz_8WbJCPmAqa3Mxw5zw1ts2SyGI"
    "/gviz/tq?tqx=out:csv&gid="
)

CLASS_NAMES = {
    "warrior": "戰士",
    "assassin": "刺客",
    "ranger": "射手",
    "guard": "守衛",
    "mage": "法師",
    "support": "牧師",
}
SHEET_GIDS = {
    "warrior": "1719387111",
    "assassin": "3323578",
    "ranger": "1378722359",
    "guard": "1397375533",
    "mage": "520944077",
    "support": "1689521295",
}
TIER_PATTERN = re.compile(r"(?:SS|S\+|S|A\+|A|B|C)")
EXPLANATION_PREFIXES = (
    "全陣營通用",
    "屬於綁",
    "特定陣營",
    "仍有強度",
    "強度普通",
    "投入資源",
    "不值得",
)


def clean(value: str) -> str:
    return " ".join(value.split()).strip()


def split_lines(value: str) -> list[str]:
    return [clean(part) for part in value.splitlines() if clean(part)]


def split_functions(value: str) -> list[str]:
    result: list[str] = []
    for line in split_lines(value):
        for item in re.split(r"[、，,/]+", line):
            item = clean(item).strip("?")
            if item and item not in {"其他陣營", "定位", "神格"}:
                result.append(item)
    return list(dict.fromkeys(result))


def is_character_row(row: list[str]) -> bool:
    if len(row) < 7:
        return False
    tier = clean(row[1])
    name = clean(row[2])
    return (
        bool(TIER_PATTERN.fullmatch(tier))
        and bool(name)
        and len(name) < 45
        and not name.startswith(EXPLANATION_PREFIXES)
    )


def character_id(class_key: str, name: str) -> str:
    slug = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "-", name).strip("-")
    return f"{class_key}-{slug.lower()}"


def import_csv(path: Path, class_key: str) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.reader(file))

    records: list[dict] = []
    for row in rows[2:]:
        if not is_character_row(row):
            continue
        padded = row + [""] * (32 - len(row))
        name = clean(padded[2])
        notes = split_lines(padded[24]) + split_lines(padded[31])
        functions = split_functions(padded[7])
        records.append(
            {
                "id": character_id(class_key, name),
                "name": name,
                "class_name": CLASS_NAMES[class_key],
                "main_faction": clean(padded[5]),
                "secondary_faction": clean(padded[6]),
                "skills": [],
                "special_functions": functions,
                "aliases": split_lines(padded[3]),
                "image_url": "",
                "quality": normalize_quality(clean(padded[4])),
                "tier": clean(padded[1]),
                "guide_notes": "\n".join(notes),
                "source": {
                    "kind": "guide",
                    "title": "龍魂旅人全角色養成指南（停更）",
                    "url": SHEET_URL + SHEET_GIDS[class_key],
                    "accessed_at": date.today().isoformat(),
                    "confidence": "medium",
                },
            }
        )
    return [
        record for record in records
        if is_legendary_or_higher(record["quality"])
    ]


def main() -> None:
    records: list[dict] = []
    if OUTPUT.exists():
        existing = json.loads(OUTPUT.read_text(encoding="utf-8"))
        records.extend(
            record
            for record in existing
            if record.get("source", {}).get("kind") == "official"
        )
    for path in sorted(RAW_DIR.glob("*.csv")):
        class_key = path.stem
        if class_key in CLASS_NAMES:
            records.extend(import_csv(path, class_key))

    records.sort(key=lambda record: (record["class_name"], record["name"]))
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"已匯入 {len(records)} 筆角色資料：{OUTPUT}")


if __name__ == "__main__":
    main()

"""依目前角色技能描述重新整理並匯出能力分類清單。"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dragon_team_builder.abilities import stroke_sort_key
from dragon_team_builder.data_loader import load_characters


DATA_PATH = ROOT / "src" / "dragon_team_builder" / "data" / "characters.json"
ALL_OUTPUT = ROOT / "abilities_all.csv"
SINGLE_OUTPUT = ROOT / "abilities_single_character.csv"


def collect() -> dict[str, list[object]]:
    grouped: dict[str, list[object]] = {}
    for character in load_characters(DATA_PATH):
        for ability in character.special_functions:
            grouped.setdefault(ability, []).append(character)
    return grouped


def write_csv(path: Path, rows: list[tuple[str, str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["技能、能力", "角色名稱", "角色ID"])
        writer.writerows(rows)


def main() -> None:
    grouped = collect()
    all_rows = [
        (ability, character.name, character.id)
        for ability in sorted(grouped, key=stroke_sort_key)
        for character in sorted(grouped[ability], key=lambda item: stroke_sort_key(item.name))
    ]
    single_rows = [
        row for row in all_rows if len(grouped[row[0]]) == 1
    ]
    write_csv(ALL_OUTPUT, all_rows)
    write_csv(SINGLE_OUTPUT, single_rows)
    print(f"已匯出 {len(grouped)} 項分類、{len(all_rows)} 筆角色對應")
    print(f"單一角色分類：{len(single_rows)} 筆")


if __name__ == "__main__":
    main()

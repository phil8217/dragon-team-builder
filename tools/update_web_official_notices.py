"""更新 GitHub Pages 使用的台服官方公告清單。"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dragon_team_builder.official_updates import check_official_updates


CHARACTER_DATA = ROOT / "src" / "dragon_team_builder" / "data" / "characters.json"
WEB_NOTICE_DATA = ROOT / "web" / "data" / "official_maintenance_notices.json"


def atomic_write_json(path: Path, payload: dict) -> None:
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


def load_existing_notices() -> dict:
    if not WEB_NOTICE_DATA.exists():
        return {}
    payload = json.loads(WEB_NOTICE_DATA.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("網頁版公告資料必須是 JSON 物件。")
    return payload


def main() -> None:
    characters = json.loads(CHARACTER_DATA.read_text(encoding="utf-8-sig"))
    if not isinstance(characters, list):
        raise ValueError("角色資料必須是 JSON 陣列。")

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

    notices = report.get("notices", [])
    payload = {
        "source": "https://sod.game-beans.com/jx/sodNotice/index.html",
        "accessed_at": report.get("checked_at", ""),
        "index_pages": 2,
        "notice_count": len(notices),
        "notices": notices,
    }
    atomic_write_json(WEB_NOTICE_DATA, payload)
    print(
        f"官方公告檢查完成：{len(notices)} 筆公告，"
        f"本次變更 {len(report.get('changed_notices', []))} 筆。"
    )


if __name__ == "__main__":
    main()

"""下載角色圖片並把本地資源路徑寫回角色資料。"""

from __future__ import annotations

import hashlib
import json
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "src" / "dragon_team_builder" / "data" / "characters.json"
IMAGE_DIR = ROOT / "src" / "dragon_team_builder" / "data" / "images"


def download(record: dict) -> tuple[str, str]:
    url = record.get("image_url", "")
    if not url:
        return record["id"], ""
    extension = ".jpg" if ".jpg" in url.lower() else ".webp"
    filename = hashlib.sha256(record["id"].encode("utf-8")).hexdigest()[:16]
    target = IMAGE_DIR / f"{filename}{extension}"
    if not target.exists():
        request = urllib.request.Request(
            url, headers={"User-Agent": "DragonTeamBuilder/0.1"}
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            target.write_bytes(response.read())
    return record["id"], f"data/images/{target.name}"


def main() -> None:
    records = json.loads(DATA.read_text(encoding="utf-8"))
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=12) as pool:
        downloaded = dict(pool.map(download, records))
    for record in records:
        record["image_file"] = downloaded.get(record["id"], "")
    by_id = {record["id"]: record for record in records}
    for record in records:
        if record["image_file"] or not record["id"].endswith("-專武"):
            continue
        base = by_id.get(record["id"][:-3])
        if base:
            record["image_file"] = base.get("image_file", "")
            record["image_url"] = base.get("image_url", "")
    DATA.write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"已下載 {sum(bool(value) for value in downloaded.values())} 張角色圖片")


if __name__ == "__main__":
    main()

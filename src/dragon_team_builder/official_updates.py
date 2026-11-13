"""台服官方公告的每日差異檢查。"""

from __future__ import annotations

import hashlib
import html
import json
import os
import re
import shutil
import tempfile
import urllib.request
from datetime import date, datetime
from html.parser import HTMLParser
from pathlib import Path


BASE_URL = "https://sod.game-beans.com"
INDEX_URL = BASE_URL + "/jx/sodNotice/index{}.html"
NOTICE_TITLE_KEYWORDS = ("維護", "更新")
MAINTENANCE_CATALOG_PATH = (
    Path(__file__).resolve().parent / "data" / "official_maintenance_notices.json"
)
SKILL_TYPE_ORDER = {
    "天賦": 0,
    "奧義": 1,
    "絕技": 2,
    "秘技": 3,
    "特技": 4,
}


def sort_skill_records(skills: list[dict]) -> list[dict]:
    """依遊戲技能顯示順序排序，未知類型則保留在最後。"""

    return sorted(
        skills,
        key=lambda skill: SKILL_TYPE_ORDER.get(
            skill.get("skill_type", ""),
            len(SKILL_TYPE_ORDER),
        ),
    )


class _TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"script", "style", "noscript"}:
            self.skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self.skip_depth:
            self.skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self.skip_depth and data.strip():
            self.parts.append(" ".join(data.split()))


def _fetch(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "DragonTeamBuilder/0.1"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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


def _visible_text(content: str) -> str:
    parser = _TextParser()
    parser.feed(content)
    return "\n".join(parser.parts)


def _notice_title(content: str) -> str:
    match = re.search(
        r'<div class="news-tit">(.*?)</div>',
        content,
        flags=re.S,
    )
    if match:
        return html.unescape(_visible_text(match.group(1)))
    match = re.search(r"<h1[^>]*>(.*?)</h1>", content, flags=re.S)
    return html.unescape(_visible_text(match.group(1))) if match else ""


def _links_from_index(content: str) -> list[str]:
    links = re.findall(
        r'href="(https://sod\.game-beans\.com/jx/sodNotice/[^"]+\.html)"',
        content,
    )
    return list(dict.fromkeys(links))


def _notice_date(url: str) -> str:
    match = re.search(r"/(\d{8})/", url)
    if not match:
        return ""
    value = match.group(1)
    return f"{value[:4]}-{value[4:6]}-{value[6:]}"


def _other_optimization_section(text: str) -> str:
    lines = text.splitlines()
    start = next(
        (
            index
            for index, line in enumerate(lines)
            if (
                "其他優化及修復內容" in line
                or (
                    "其他" in line
                    and index + 1 < len(lines)
                    and "優化及修復內容" in lines[index + 1]
                )
            )
        ),
        None,
    )
    if start is None:
        return ""
    section = []
    for line in lines[start + 1:]:
        if "儲值推薦" in line or line.startswith("----"):
            break
        section.append(line)
    return "\n".join(section)


def _new_character_names(text: str) -> list[str]:
    names = []
    for line in text.splitlines():
        if "全新" not in line or "幻靈" not in line:
            continue
        match = re.search(r"幻靈[－-]([^\n]+)", line)
        if match:
            name = match.group(1).strip()
            if name and name not in names:
                names.append(name)
    for match in re.finditer(
        r"全新[^。\n]{0,30}?幻靈([^。\n]+?)(?:召喚機率|召喚)",
        text,
    ):
        name = match.group(1).strip()
        if name and name not in names:
            names.append(name)
    return names


def _has_character_update(
    section: str,
    characters: list[dict],
) -> bool:
    if not section or not re.search(r"調整|優化|修復", section):
        return False
    for character in characters:
        names = [
            character.get("name", ""),
            *character.get("aliases", []),
            *re.split(r"\s*[•・·]\s*", character.get("name", "")),
        ]
        if any(name and name in section for name in names):
            return True
    return False


def check_official_updates(
    characters: list[dict],
    output_dir: str | Path,
) -> dict:
    """下載公告並產生差異報告，不修改角色資料。"""

    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    old_index_path = directory / "notice_index.json"
    old_index: dict = {}
    if old_index_path.exists():
        try:
            old_index = json.loads(
                old_index_path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError):
            old_index = {}
    old_notices = {
        item.get("url"): item
        for item in old_index.get("notices", [])
        if isinstance(item, dict) and item.get("url")
    }
    index_contents = [
        _fetch(INDEX_URL.format("" if page == 1 else f"_{page}"))
        for page in (1, 2)
    ]
    urls = list(dict.fromkeys(
        url
        for content in index_contents
        for url in _links_from_index(content)
    ))
    notices = []
    changed = []
    for url in urls:
        content = _fetch(url)
        text = _visible_text(content)
        title = _notice_title(content)
        if not any(keyword in title for keyword in NOTICE_TITLE_KEYWORDS):
            continue
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        other_optimization = _other_optimization_section(text)
        notice = {
            "url": url,
            "title": title,
            "date": _notice_date(url),
            "new_characters": _new_character_names(text),
            "updates_character_values": _has_character_update(
                other_optimization,
                characters,
            ),
            "content_hash": digest,
        }
        notices.append(notice)
        if old_notices.get(url, {}).get("content_hash") != digest:
            changed.append(notice)

    checked_at = date.today().isoformat()
    catalog_notices = []
    if MAINTENANCE_CATALOG_PATH.exists():
        try:
            catalog = json.loads(
                MAINTENANCE_CATALOG_PATH.read_text(encoding="utf-8")
            )
            catalog_notices = [
                item for item in catalog.get("notices", [])
                if isinstance(item, dict) and item.get("url")
            ]
        except (OSError, json.JSONDecodeError):
            catalog_notices = []
    notices_by_url = {
        notice["url"]: notice for notice in catalog_notices
    }
    notices_by_url.update({notice["url"]: notice for notice in notices})
    index_payload = {
        "source": BASE_URL + "/jx/sodNotice/index.html",
        "accessed_at": checked_at,
        "index_pages": 2,
        "notice_count": len(notices),
        "notices": notices,
    }
    report = {
        "checked_at": checked_at,
        "notices": list(notices_by_url.values()),
        "changed_notices": changed,
        "message": "列出台服官方維護公告與角色變更狀態。",
    }
    _atomic_write(
        old_index_path,
        json.dumps(index_payload, ensure_ascii=False, indent=2) + "\n",
    )
    _atomic_write(
        directory / "official_update_report.json",
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
    )
    return report


def apply_official_updates(
    records: list[dict],
    notice_urls: list[str],
    data_path: str | Path,
    version_path: str | Path,
    backup_dir: str | Path,
) -> dict:
    """將官方公告中的角色技能資料套用到可寫入的角色資料副本。"""

    source_path = Path(data_path)
    if not source_path.exists():
        return {"updated_characters": [], "backup": ""}
    payload = json.loads(source_path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, list):
        raise ValueError("角色資料必須是陣列。")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = Path(backup_dir) / f"characters_{timestamp}.json"
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, backup_path)
    updated = []
    for url in notice_urls:
        content = _fetch(url)
        text = _visible_text(content)
        blocks = _skill_blocks(text)
        section = _other_optimization_section(text)
        skill_context = _skill_character_context(text)
        for record in payload:
            names = [
                record.get("name", ""),
                *record.get("aliases", []),
                *re.split(r"\s*[•・·]\s*", record.get("name", "")),
            ]
            if not any(
                name and name in section + "\n" + skill_context
                for name in names
            ):
                continue
            changed = False
            if any(name and name in skill_context for name in names):
                for skill_type, skill_name, description in blocks:
                    for skill in record.get("skills", []):
                        if skill.get("skill_type") != skill_type:
                            continue
                        skill["description"] = description
                        if skill_name:
                            skill["name"] = skill_name
                        changed = True
                        break
            if section or changed:
                record.setdefault("official_updates", []).append({
                    "url": url,
                    "date": _notice_date(url),
                    "section": section,
                    "applied_at": date.today().isoformat(),
                })
                changed = True
            if changed and record.get("id") not in updated:
                updated.append(record.get("id", ""))
    for record in payload:
        skills = record.get("skills", [])
        sorted_skills = sort_skill_records(skills)
        if sorted_skills != skills:
            record["skills"] = sorted_skills
            if record.get("id") not in updated:
                updated.append(record.get("id", ""))
    if updated:
        character_json = json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        ) + "\n"
        if not isinstance(json.loads(character_json), list):
            raise ValueError("套用後角色資料格式無效。")
        _atomic_write(source_path, character_json)
        version_file = Path(version_path)
        version = {}
        if version_file.exists():
            version = json.loads(
                version_file.read_text(encoding="utf-8")
            )
        version.update({
            "version": date.today().isoformat(),
            "updated_at": date.today().isoformat(),
            "character_count": len(payload),
        })
        version_file.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write(
            version_file,
            json.dumps(version, ensure_ascii=False, indent=2) + "\n",
        )
    else:
        backup_path.unlink(missing_ok=True)
    return {
        "updated_characters": updated,
        "backup": str(backup_path) if updated else "",
    }


def _skill_blocks(text: str) -> list[tuple[str, str, str]]:
    blocks = []
    current: tuple[str, str, list[str]] | None = None
    pattern = re.compile(
        r"^(天賦|奧義|絕技|秘技|特技)\s*[-－—:：]+\s*(.*)$"
    )
    for line in text.splitlines():
        stripped = line.strip()
        if current is not None and (
            stripped.startswith(("限定召喚卡池", "活動-", "活動－", "★其他", "【儲值推薦】", "新聞列表"))
            or stripped.startswith("----")
        ):
            break
        match = pattern.match(line.strip())
        if match:
            if current is not None:
                blocks.append((
                    current[0],
                    current[1],
                    "\n".join(current[2]).strip(),
                ))
            current = (match.group(1), match.group(2).strip(), [])
        elif current is not None:
            if stripped and not line.startswith("★★"):
                if not current[1]:
                    current = (current[0], stripped, current[2])
                else:
                    current[2].append(stripped)
    if current is not None:
        blocks.append((
            current[0],
            current[1],
            "\n".join(current[2]).strip(),
        ))
    return [
        block for block in blocks
        if block[2]
    ]


def _skill_character_context(text: str) -> str:
    lines = text.splitlines()
    first_skill = next(
        (
            index for index, line in enumerate(lines)
            if re.match(
                r"^(天賦|奧義|絕技|秘技|特技)\s*[-－—:：]+",
                line.strip(),
            )
        ),
        None,
    )
    if first_skill is None:
        return ""
    return "\n".join(lines[max(0, first_skill - 12):first_skill])

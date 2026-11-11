"""抓取台服官方公告，並以目前角色資料做文字比對。"""

from __future__ import annotations

import html
import json
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NOTICE_DIR = ROOT / "data" / "tw_notices"
CHARACTER_DATA = ROOT / "src" / "dragon_team_builder" / "data" / "characters.json"
BASE = "https://sod.game-beans.com"
INDEX_URL = BASE + "/jx/sodNotice/index{}.html"
ACCESS_DATE = "2026-11-11"


class TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self.skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self.skip_depth:
            self.skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self.skip_depth and data.strip():
            self.parts.append(" ".join(data.split()))


def fetch(url: str) -> str:
    request = urllib.request.Request(
        url, headers={"User-Agent": "DragonTeamBuilder/0.1"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def links_from_index(content: str) -> list[str]:
    links = re.findall(
        r'href="(https://sod\.game-beans\.com/jx/sodNotice/[^"]+\.html)"',
        content,
    )
    return list(dict.fromkeys(links))


def visible_text(content: str) -> str:
    parser = TextParser()
    parser.feed(content)
    return "\n".join(parser.parts)


def notice_title(content: str) -> str:
    match = re.search(
        r'<div class="news-tit">(.*?)</div>',
        content,
        flags=re.S,
    )
    return visible_text(match.group(1)) if match else ""


def filename(url: str) -> str:
    return url.rsplit("/", 1)[-1]


def main() -> None:
    NOTICE_DIR.mkdir(parents=True, exist_ok=True)
    index_urls = [
        INDEX_URL.format("" if page == 1 else f"_{page}")
        for page in range(1, 44)
    ]
    index_contents: list[str] = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        for page, content in zip(range(1, 44), pool.map(fetch, index_urls)):
            path = NOTICE_DIR / f"index_{page}.html"
            path.write_text(content, encoding="utf-8")
            index_contents.append(content)

    urls = list(dict.fromkeys(
        url for content in index_contents for url in links_from_index(content)
    ))
    with ThreadPoolExecutor(max_workers=12) as pool:
        contents = list(pool.map(fetch, urls))

    notices = []
    for url, content in zip(urls, contents):
        path = NOTICE_DIR / filename(url)
        path.write_text(content, encoding="utf-8")
        text = visible_text(content)
        title = notice_title(content)
        notices.append(
            {
                "url": url,
                "title": html.unescape(title),
                "text": text,
            }
        )

    characters = json.loads(CHARACTER_DATA.read_text(encoding="utf-8"))
    report = []
    for character in characters:
        names = [character["name"], *character.get("aliases", [])]
        matches = [
            {
                "url": notice["url"],
                "title": notice["title"],
                "mentions": [
                    name for name in names if name and name in notice["text"]
                ],
            }
            for notice in notices
            if any(name and name in notice["text"] for name in names)
        ]
        report.append(
            {
                "character_id": character["id"],
                "character_name": character["name"],
                "notice_matches": matches,
            }
        )

    (NOTICE_DIR / "notice_index.json").write_text(
        json.dumps(
            {
                "source": "https://sod.game-beans.com/jx/sodNotice/index.html",
                "accessed_at": ACCESS_DATE,
                "index_pages": 43,
                "notice_count": len(notices),
                "notices": [
                    {
                        "url": notice["url"],
                        "title": notice["title"],
                    }
                    for notice in notices
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (NOTICE_DIR / "character_notice_matches.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    new_characters = []
    for notice in notices:
        for match in re.finditer(
            r"全新幻靈[－-]([^<\n]+)",
            notice["text"],
        ):
            name = re.split(r"[（(]", match.group(1))[0].strip()
            if name and name not in new_characters:
                new_characters.append(name)
    (NOTICE_DIR / "official_new_characters.json").write_text(
        json.dumps(
            {
                "source": "https://sod.game-beans.com/jx/sodNotice/index.html",
                "accessed_at": ACCESS_DATE,
                "characters": new_characters,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"索引頁：43；公告正文：{len(notices)}")
    print(
        "有官方公告提及的角色："
        f"{sum(bool(item['notice_matches']) for item in report)}"
    )


if __name__ == "__main__":
    main()

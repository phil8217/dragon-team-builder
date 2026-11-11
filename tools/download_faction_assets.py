"""下載陣營 logo。"""

from pathlib import Path
import urllib.request

from dragon_team_builder.factions import FACTIONS


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "src" / "dragon_team_builder" / "data" / "factions"
BASE = "https://www.dragoncompanion.com/assets/media/character/factions/"


def main() -> None:
    TARGET.mkdir(parents=True, exist_ok=True)
    for info in FACTIONS.values():
        path = TARGET / f"{info.key}.webp"
        request = urllib.request.Request(
            BASE + f"{info.key}.webp",
            headers={"User-Agent": "DragonTeamBuilder/0.1"},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            path.write_bytes(response.read())
    print(f"已下載 {len(FACTIONS)} 個陣營 logo")


if __name__ == "__main__":
    main()

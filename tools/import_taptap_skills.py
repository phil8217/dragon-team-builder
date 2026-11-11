"""補充 TapTap 角色攻略中可核實的中文技能資料。"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHARACTER_DATA = ROOT / "src" / "dragon_team_builder" / "data" / "characters.json"
SOURCE_URL = "https://www.taptap.cn/moment/680801847132292757"
SOURCE = {
    "kind": "community",
    "title": "TapTap：角色介绍・白虎（四圣）体验心得",
    "url": SOURCE_URL,
    "accessed_at": "2026-11-11",
    "confidence": "medium",
}

WHITE_TIGER_SKILLS = [
    (
        "天賦",
        "百裂腿",
        "自身無法造成暴擊，但每進行第 3 次普攻，會對目標及其身後中等扇形範圍的敵人造成自身攻擊 250% 的物理傷害。"
        "\n2級：每當我方有單位被擊敗時，自身獲得 1 層【遺言】，每層【遺言】可提升自身 1.5% 的攻擊。"
        "\n3級：提升自身 10% 攻擊和 3% 的攻速。"
        "\n4級：釋放【空中百裂腿】時，自身可驅散所有減益狀態。"
        "\n7級：處於【狂野】狀態時，自身免疫屬性類減益狀態。",
    ),
    (
        "奧義",
        "空中百裂腿",
        "消耗自身當前生命值的 30%，對單一目標造成自身攻擊 910% 的物理傷害，技能持續期間額外提升自身 40% 的生命值轉化效果。",
    ),
    (
        "絕技",
        "旋圓蹴",
        "跳至目標身後，對較大扇形範圍內的敵方單位造成自身攻擊 320% 的物理傷害。",
    ),
    (
        "秘技",
        "百裂連打",
        "當自身血量降低時會積攢怒氣，怒氣滿時進入【狂野】狀態。處於【狂野】狀態時，攻擊提升 10%，普攻會強化為【百裂連打】，【百裂連打】每次都能觸發【百裂腿】的範圍傷害。",
    ),
    (
        "特技",
        "透體之勁",
        "自身所有攻擊無視目標 15% 的物防。當自身未處於減益狀態時，該效果翻倍。",
    ),
]

OTHER_TAPTAP_SKILLS = {
    "霞": (
        "https://www.taptap.cn/moment/835468935003376948",
        [
            ("天賦", "奪刃卸甲", "釋放【幻櫻天落】後，自身進入蟄伏狀態，期間不再進行普通攻擊並獲得 60% 減傷、600 格擋，每秒獲得 1 層【奪勢】，持續 10 秒。\n2級：【櫻幕恩澤】額外獲得 2 秒免疫傷害。\n3級：提高自身 15% 攻擊。\n4級：受到【下次奧義能耗+1】效果時，清除該效果並對來源釋放【櫻霧一閃】。每 2 秒至多觸發 1 次。\n7級：自身釋放主動技能後，獲得 2 層【奪勢】。"),
            ("奧義", "幻櫻天落", "選擇單體目標閃現至目標身前，從半空中向目標發動斬擊，造成自身攻擊力 1350% 的物理傷害，該傷害必定暴擊。"),
            ("絕技", "櫻霧一閃", "使自身獲得 1 秒不可選中，閃現至目標幻靈身後進行攻擊，附加 5 秒【沉默】並造成自身攻擊力 800% 的物理傷害。"),
            ("秘技", "攻守兼備", "戰鬥中，提高自身 10% 雙防。釋放【櫻霧一閃】時回復 20% 怒氣值。自身損失血量時會回復怒氣，怒氣滿時進入【狂野】狀態，處於【狂野】狀態時，自身造成的傷害無視目標 10% 物防。"),
            ("特技", "櫻幕恩澤", "清除自身所有減益狀態，回復自身 20% 最大生命值並獲得 1 個隨機【祝福類增益】。當自身同時擁有【士氣】和【鬥志】時，進入【恩賜】狀態。若釋放【櫻幕恩澤】時自身處於【恩賜】狀態，則額外向一個我方幻靈或巨龍釋放，使目標中等圓形範圍內的我方單位獲得相同效果。技能結束後退出【恩賜】狀態。"),
        ],
    ),
    "莉莉絲": (
        "https://www.taptap.cn/moment/765990323745719290",
        [
            ("天賦", "暗夜回響", "莉莉絲擁有比一般近戰幻靈更遠的攻擊距離。自身技能造成傷害時，有 50% 機率對目標附加【苦痛回響】，持續 8 秒，不可疊層。目標每被降低 10% 被治療效果，該機率提高 3%。我方其他幻靈的普攻或主動技能對持有【苦痛回響】的敵方單位造成傷害後，莉莉絲額外對所有持有【苦痛回響】的敵方單位追加實際傷害值 310% 的魔法傷害，該傷害不會觸發暴擊、閃避和格擋。\n2級：每對攜帶【苦痛回響】的目標造成一次傷害，自身回復攻擊 20% 的血量和 5% 怒氣。\n3級：提高自身 10% 生命和 4% 生命轉化。\n4級：【影刃亂舞】可觸發【懲戒】效果，觸發時使目標奧義冷卻額外增加 2 秒。\n7級：處於【狂野】狀態的我方幻靈對持有【苦痛回響】的敵方單位造成傷害時，提高 50% 增傷。"),
            ("奧義", "滅亡之歌", "對扇形範圍的敵方單位造成 3 次自身攻擊 340% 的魔法傷害。對已經攜帶【苦痛回響】的目標額外附加 4 秒【沉默】。"),
            ("絕技", "影刃亂舞", "對較大圓形範圍內的敵方單位各發射 1 枚魔法彈，造成自身攻擊 280% 的魔法傷害並使目標奧義冷卻增加 2 秒。戰鬥開始時立即閃現至敵方隊伍中心，並釋放 1 次本技能。處於【狂野】狀態時，對每個目標額外發射 1 枚魔法彈，額外魔法彈傷害提升至自身攻擊的 420%，但不會增加目標奧義冷卻。"),
            ("秘技", "噬能雙刃", "我方幻靈偷取敵方單位屬性時，自身提高 3% 生命轉化，持續到戰鬥結束，可觸發 20 次。我方幻靈觸發【懲戒】時對目標附加【被治療降低】。"),
            ("特技", "夢魘掠奪", "施加【苦痛回響】時，額外偷取目標 2.4% 攻擊，持續 8 秒，可疊加 5 層。"),
        ],
    ),
}


def main() -> None:
    records = json.loads(CHARACTER_DATA.read_text(encoding="utf-8"))
    updated = 0
    for record in records:
        character_key = "白虎" if "白虎" in record["name"] else next(
            (key for key in OTHER_TAPTAP_SKILLS if key in record["name"]),
            None,
        )
        if character_key is None:
            continue
        if character_key == "白虎":
            source_url = SOURCE_URL
            skill_data = WHITE_TIGER_SKILLS
        else:
            source_url, skill_data = OTHER_TAPTAP_SKILLS[character_key]
        source = {**SOURCE, "url": source_url}
        existing = {
            skill["skill_type"]: skill
            for skill in record["skills"]
        }
        skills = []
        for skill_type, name, description in skill_data:
            skill = existing.get(skill_type, {})
            skill.update(
                {
                    "name": name,
                    "description": description,
                    "skill_type": skill_type,
                    "sources": [source],
                    "tags": skill.get("tags", []),
                    "metrics": skill.get("metrics", []),
                }
            )
            skills.append(skill)
        record["skills"] = skills
        updated += 1
    if not updated:
        raise RuntimeError("找不到任何可更新的 TapTap 角色資料")
    CHARACTER_DATA.write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"已更新 {updated} 名 TapTap 角色技能與天賦")


if __name__ == "__main__":
    main()

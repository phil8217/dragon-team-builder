"""加入台服官方公告已確認、但攻略資料尚未收錄的角色。"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "src" / "dragon_team_builder" / "data" / "characters.json"
NOTICE_URL = "https://sod.game-beans.com/jx/sodNotice/20261104/8323.html"
URD_NOTICE_URL = "https://sod.game-beans.com/jx/sodNotice/20261111/8346.html"
ERATO_IMAGE_URL = (
    "https://tw-media.game-beans.com/media/pictures/sod/T2026110302.jpg"
)
URD_IMAGE_URL = (
    "https://tw-media.game-beans.com/media/pictures/sod/T2026111001.jpg"
)
SOURCE = {
    "kind": "official",
    "title": "台服官方公告：11月4日維護更新",
    "url": NOTICE_URL,
    "accessed_at": "2026-11-11",
    "confidence": "high",
}


def skill(name: str, skill_type: str, description: str, tags: list[str]) -> dict:
    return {
        "name": name,
        "description": description,
        "skill_type": skill_type,
        "tags": tags,
        "metrics": [],
        "sources": [SOURCE],
    }


ERATO = {
    "id": "support-戀歌謬斯-艾拉托",
    "name": "戀歌謬斯 • 艾拉托",
    "class_name": "牧師",
    "main_faction": "聖堂",
    "secondary_faction": "元素",
    "skills": [
        skill(
            "柔音共鳴",
            "天賦",
            "當我方其他幻靈獲得祝福類增益時，額外獲得一個隨機屬性類增益，同一目標4秒內至多觸發一次。戰鬥開始時，永久提高自身2%攻擊和雙防，此後每2秒觸發一次。2級：當敵方幻靈被施加基礎元素減益時，對其施加一個隨機屬性類減益，每秒至多觸發一次。3級：提高自身10%攻擊和5技能急速。4級：自身技能對同一目標施加4次屬性類減益後，對其施加禁療。7級：為我方其他幻靈施加屬性類增益時，為自身施加隨機屬性類增益。",
            ["增益", "減益", "禁療"],
        ),
        skill(
            "星輝合唱",
            "奧義",
            "耗能4，冷卻20秒。生成極大範圍光環，持續7秒。光環內我方其他幻靈或巨龍獲得星願祝福：分享自身當前攻擊、生命和雙防的15%，至多不超過入場面板的200%。奧義持續期間，每3秒分享自身50%當前護盾，至多不超過自身生命200%，持續6秒。奧義結束時，驅散光環內我方幻靈或巨龍2個減益狀態。星願祝福不可驅散。",
            ["護盾", "增益", "驅散"],
        ),
        skill(
            "星願揮舞",
            "絕技",
            "冷卻10秒。對自己和生命值最低的我方單位（幻靈優先）施放星願，回復目標自身最大生命10%的血量並施加隨機祝福類增益。每顆星願額外獲得0.5個奧義點。當自身同時擁有士氣和鬥志時，進入恩賜狀態；處於恩賜狀態時，額外施放一顆星願。奧義施放期間每2秒施放一顆星願。",
            ["治療", "增益", "回復奧義"],
        ),
        skill(
            "和聲守護",
            "秘技",
            "戰鬥中提供自身15%生命。攜帶4個及以上增益狀態的我方幻靈，普攻附加隨機基礎元素減益；每個我方其他幻靈2秒內至多觸發一次。",
            ["增益", "減益"],
        ),
        skill(
            "踏音成譜",
            "特技",
            "施放奧義時，獲得自身最大生命值40%的護盾，持續6秒。之後奧義持續期間，每3秒獲得自身最大生命值40%的護盾，持續6秒。",
            ["護盾"],
        ),
        skill(
            "神格技能",
            "神格",
            "柔音共鳴額外提高目標40%奧義增傷，持續6秒。",
            ["增傷"],
        ),
    ],
    "special_functions": [
        "分享屬性",
        "群體護盾",
        "群體增益",
        "治療",
        "驅散減益",
        "元素減益",
    ],
    "aliases": ["艾拉托", "戀歌謬斯"],
    "image_url": ERATO_IMAGE_URL,
    "quality": "傳說+",
    "tier": "",
    "guide_notes": "台服 2026年11月4日官方公告新增角色。",
    "source": SOURCE,
}

URD = {
    "id": "assassin-裁命女神-烏爾德",
    "name": "裁命女神 • 烏爾德",
    "class_name": "刺客",
    "main_faction": "彼岸",
    "secondary_faction": "聖堂",
    "skills": [
        skill(
            "亡語迴響",
            "天賦",
            "每當有我方單位被擊敗時，自身獲得1層遺言。遺言達15層時，普攻強化為對前方中等扇形範圍造成自身攻擊200%的物理傷害；達20層時，彼光餽贈效果改為全部觸發；達25層時永久免疫減益；達30層時普攻附加自身攻擊30%的真實傷害。2級：每進入1次恩賜狀態，永久提高15%攻擊並獲得5層遺言，最多6次。3級：施放主動技能時獲得隨機屬性類增益和4秒不可選中；施放奪命羅網時額外施加斷命。4級：移行換影改為與目標交換位置，並使其中等圓形範圍內我方單位索敵該目標。5級提高10%攻擊和8%攻速，7級提高16%攻速。斷命期間無法獲得增益或護盾，降低70%攻擊、攻速、雙防及被治療效果，持續15秒且不可驅散。",
            ["增傷", "免疫減益", "真實傷害", "不可選中"],
        ),
        skill(
            "奪命羅網",
            "奧義",
            "耗能3，冷卻20秒。向目標突進，驅散其所有增益，造成目標最大生命值1%乘以自身遺言層數的真實傷害（不超過自身攻擊15%乘以遺言層數）及自身攻擊1250%的物理傷害。隨後展開領域，使自身較大圓形範圍內所有非我方同陣營單位降低120%減傷和奧義減傷，持續8秒。",
            ["驅散", "真實傷害", "減傷", "降奧義減傷"],
        ),
        skill(
            "裁決連剪",
            "絕技",
            "冷卻12秒。連續剪擊三次，每次對前方中等扇形範圍造成自身攻擊250%的物理傷害，第三次傷害翻倍並驅散一個增益，施放期間自身免疫控制。若處於恩賜狀態，每次傷害附帶自身攻擊75%的真實傷害，施放後回復自身35%生命並解除恩賜狀態。",
            ["驅散", "免疫控制", "真實傷害", "治療"],
        ),
        skill(
            "彼光餽贈",
            "秘技",
            "提高自身15%雙防。在場時，敵方被驅散增益或護盾，或我方被驅散減益後，隨機觸發一種效果：我方彼岸再臨幻靈獲得遺言並提高彼岸再臨單位增傷和減傷，或自身與一名我方幻靈（優先聖堂榮光）獲得隨機祝福類增益和屬性類增益。",
            ["增益", "增傷", "減傷", "護盾"],
        ),
        skill(
            "移行換影",
            "特技",
            "戰鬥開始後獲得2秒免疫控制，閃現至與自身站位中心對稱的敵方幻靈身前（無視守衛阻攔），驅散其護盾和所有增益，造成自身攻擊650%的物理傷害並附加斷命和1秒眩暈。",
            ["免疫控制", "驅散", "護盾", "眩暈"],
        ),
        skill(
            "神格技能",
            "神格",
            "奪命羅網造成的真實傷害提高30%。",
            ["真實傷害"],
        ),
    ],
    "special_functions": [
        "遺言疊層",
        "驅散增益與護盾",
        "真實傷害",
        "免疫控制",
        "無視守衛阻攔",
        "斷命",
    ],
    "aliases": ["烏爾德", "裁命女神"],
    "image_url": URD_IMAGE_URL,
    "quality": "傳說‧神話",
    "tier": "",
    "guide_notes": "台服 2026年11月11日官方公告新增角色。",
    "source": {
        **SOURCE,
        "title": "台服官方公告：11月11日維護更新",
        "url": URD_NOTICE_URL,
    },
}


def main() -> None:
    records = json.loads(DATA.read_text(encoding="utf-8"))
    records = [
        record
        for record in records
        if record["id"] not in {ERATO["id"], URD["id"]}
    ]
    records.extend([ERATO, URD])
    records.sort(key=lambda record: (record["class_name"], record["name"]))
    DATA.write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"已加入：{ERATO['name']}")


if __name__ == "__main__":
    main()

"""角色技能與能力篩選用的標準名稱。"""

import re

from .mechanics import ELEMENTAL_MECHANICS


ABILITY_RENAMES = {
    "召喚物": "召喚",
    "菁英召喚物": "召喚",
    "複製召喚物": "召喚",
    "召喚增傷": "召喚物增益",
    "強化召喚物": "召喚物增益",
    "攜盾增傷": "護盾增傷",
    "疊盾增傷": "護盾增傷",
    "懲戒沉默": "沉默",
    "懲戒減費": "懲戒",
    "驅散減益": "解除異常",
    "驅散異常": "解除異常",
    "驅散增益": "驅散",
    "驅散增益與護盾": "驅散",
    "群盾": "護盾",
    "群體護盾": "護盾",
    "羣盾": "護盾",
    "羣體護盾": "護盾",
    "加盾": "護盾",
    "開場盾": "護盾",
    "輔助增傷": "增傷",
    "自身減傷": "減傷",
    "後排減傷": "減傷",
    "聖屏減傷": "減傷",
    "單控": "控制",
    "群控": "控制",
    "連環控制": "控制",
    "單體沉默": "沉默",
    "群體沉默": "沉默",
    "羣體沉默": "沉默",
    "開場嘲諷": "嘲諷",
    "群嘲": "嘲諷",
    "石化控場": "石化",
    "群控石化": "石化",
    "開場無敵": "無敵",
    "免疫死亡": "免死",
    "碎冰免死": "免死",
    "群體加攻": "加攻",
    "羣體加攻": "加攻",
    "AOE": "範圍輸出",
    "全圖掃射": "範圍輸出",
    "範圍打擊": "範圍輸出",
    "元素主C": "主C",
    "暗主C": "主C",
    "暗隊主C": "主C",
    "綠主C": "主C",
    "綠隊主C": "主C",
    "單點秒殺": "爆發",
    "CD減免": "技能冷卻",
    "群體CD減免": "技能冷卻",
    "羣體CD減免": "技能冷卻",
    "指定降CD": "技能冷卻",
    "偷CD": "技能冷卻",
    "刷新奧義": "技能冷卻",
    "收割刷新": "技能冷卻",
    "回復": "治療／回復",
    "治療": "治療／回復",
    "自奶": "治療／回復",
    "群補": "治療／回復",
    "羣補": "治療／回復",
    "群體回血": "治療／回復",
    "羣體回血": "治療／回復",
    "治療暴擊": "治療／回復",
    "全體加費": "奧義能耗增加",
    "防曠野加費": "奧義能耗增加",
    "減費": "奧義能耗降低",
    "奧義加減費": "奧義能耗降低",
    "全體加物防": "防禦提升",
    "加物防": "防禦提升",
    "高魔防": "防禦提升",
    "元反": "元素反應",
    "多層感電": "感電",
    "冰凍控場": "冰凍",
    "真傷": "真實傷害",
    "起來重睡!": "噩夢",
    "電角增傷": "增傷",
    "偷取攻擊": "偷取",
    "偷費": "偷取",
    "群體抗暴": "防暴",
    "羣體抗暴": "防暴",
    "大招擊退": "控制",
    "封印4技": "封印特技",
    "EX咖哩棒": "範圍輸出",
    "保人": "護盾",
    "疊遺言": "遺言疊層",
    "遺言疊加": "遺言疊層",
    "遺言疊層": "遺言疊層",
    "疊加遺言": "遺言疊層",
}

ABILITY_SPLITS = {
    "單體偷取 暴擊剋星": ("偷取", "防暴"),
    "攻防雙向提升": ("加攻", "防禦提升"),
    "回血加盾加雙防": ("治療／回復", "護盾", "防禦提升"),
    "提升攻擊.奧義增傷.減費": ("加攻", "增傷", "奧義能耗降低"),
    "霜盾援護 碎冰免死": ("護盾", "免死"),
    "疊盾加攻 羣體擊飛": ("護盾", "加攻", "控制"),
    "降減傷.雙防.治療": ("減傷降低", "防禦降低", "降療"),
    "開場控制 高頻激爆": ("控制",),
    "噩夢降雙防": ("噩夢", "防禦降低"),
}

REMOVED_ABILITIES = {
    *ELEMENTAL_MECHANICS,
    "多層感電",
    "冰凍控場",
    "主C",
    "元素主C",
    "暗主C",
    "暗隊主C",
    "綠主C",
    "綠隊主C",
    "高爆發",
    "剋制AOE角色",
    "副C",
    "副坦",
    "暗隊特攻",
    "均衡",
    "高增益",
    "高攻速",
    "自帶高階祭司",
    "持續收益",
    "傘轉陰陽 玄甲御眾",
}


def normalize_ability(value: str) -> str:
    """將資料來源中的能力名稱轉為統一名稱。"""

    return ABILITY_RENAMES.get(value, value)


def normalize_abilities(values: list[str]) -> list[str]:
    """標準化、移除元素狀態並去除重複能力。"""

    normalized: list[str] = []
    for value in values:
        if value in ABILITY_SPLITS:
            candidates = ABILITY_SPLITS[value]
        else:
            candidates = (normalize_ability(value),)
        for canonical in candidates:
            if not canonical or canonical in REMOVED_ABILITIES:
                continue
            if canonical not in normalized:
                normalized.append(canonical)
    return normalized


_CONTROL_EFFECTS = (
    ("石化", "石化"),
    ("眩暈", "暈眩"),
    ("暈眩", "暈眩"),
    ("沉默", "沉默"),
    ("麻痺", "麻痺"),
    ("魅惑", "魅惑"),
    ("嘲諷", "嘲諷"),
    ("擊退", "擊退"),
    ("擊飛", "擊飛"),
    ("牽引", "牽引"),
    ("聚怪", "聚怪"),
    ("冰凍", "冰凍"),
    ("時間暫停", "時間暫停"),
    ("時間停滯", "時間暫停"),
    ("放逐", "放逐"),
    ("封印", "封印"),
)

_ABILITY_EFFECTS = (
    ("禁止護盾", "減益-護盾-"),
    ("消除護盾", "減益-護盾-"),
    ("禁療", "減益療傷-禁療-"),
    ("降低受治療", "減益療傷-降療-"),
    ("降療", "減益療傷-降療-"),
    ("降攻速", "減益攻速-降攻速-"),
    ("攻速降低", "減益攻速-降攻速-"),
    ("降防", "減益防禦-降防-"),
    ("降低防禦", "減益防禦-降防-"),
    ("破防", "減益防禦-降防-"),
    ("降魔防", "減益防禦-降魔防-"),
    ("破魔", "減益防禦-降魔防-"),
    ("降攻", "減益攻擊-降攻-"),
    ("降低攻擊", "減益攻擊-降攻-"),
    ("減傷降低", "減益防禦-降減傷-"),
    ("降低減傷", "減益防禦-降減傷-"),
    ("增加奧義冷卻", "減益能量-加奧義冷卻-"),
    ("奧義能耗增加", "減益能量-加奧義能耗-"),
    ("加費", "減益能量-加奧義能耗-"),
    ("偷取", "減益屬性-偷取-"),
    ("反傷", "減益傷害-反傷-"),
    ("斷命", "減益-斷命-"),
    ("噩夢", "控制-噩夢-"),
    ("電火花", "減益防禦-電火花-"),
)

_BENEFIT_EFFECTS = (
    ("全體無敵", "增益-無敵-"),
    ("無敵", "增益-無敵-"),
    ("免死", "增益-免死-"),
    ("復活", "增益-復活-"),
    ("護盾", "增益-護盾-"),
    ("防禦提升", "增益防禦-提升-"),
    ("加物防", "增益防禦-提升-"),
    ("加魔防", "增益防禦-提升-"),
    ("閃避提升", "增益閃避-提升-"),
    ("閃避", "增益閃避-提升-"),
    ("加攻速", "增益攻速-提升-"),
    ("狂野加攻速", "增益攻速-提升-"),
    ("加爆傷", "增益爆擊-爆傷-"),
    ("爆傷", "增益爆擊-爆傷-"),
    ("加攻", "增益加攻-"),
    ("提升攻擊", "增益加攻-"),
    ("攻擊提升", "增益加攻-"),
    ("增傷", "增益增傷-"),
    ("治療", "增益治療-"),
    ("回復", "增益治療-"),
    ("吸血", "增益吸血-"),
    ("加怒", "增益能量-加怒-"),
    ("回費", "增益能量-回奧義-"),
    ("奧義能耗降低", "增益能量-減奧義能耗-"),
    ("減費", "增益能量-減奧義能耗-"),
    ("免疫控制", "增益免疫-控制-"),
    ("免疫異常", "增益免疫-異常-"),
    ("免疫減益", "增益免疫-減益-"),
    ("解控", "增益免疫-控制-"),
    ("解除異常", "增益淨化-"),
    ("召喚", "增益召喚-"),
    ("分身", "增益分身-"),
)


def _scope(text: str) -> str:
    """依技能描述判斷效果範圍，統一為全體、群體或單體。"""

    if re.search(r"全體|全隊|所有我方|所有敵方|我方全員", text):
        return "全體"
    if re.search(r"群|羣|範圍|附近|周圍|多名|多個|敵方單位|我方單位", text):
        return "群體"
    if re.search(r"單體|單一目標|指定目標|當前目標|一名", text):
        return "單體"
    return "單體"


def _effect_clauses(text: str, keyword: str) -> list[str]:
    """只取包含指定效果的語句，避免其他效果污染範圍判斷。"""

    clauses = re.split(
        r"[。；！？\n]+|，(?=並|且|同時|額外|對|使|令|為|回|提高|降低|獲得)"
        r"|並(?=使|為|回復|治療)",
        text,
    )
    if keyword == "治療":
        matched = [
            clause
            for clause in clauses
            if re.search(r"(?<!被)(?<!受)治療", clause)
        ]
    else:
        matched = [clause for clause in clauses if keyword in clause]
    return matched


def _effect_text(text: str, keyword: str) -> str:
    return " ".join(_effect_clauses(text, keyword))


def _effect_scopes(text: str, keyword: str) -> list[str]:
    if keyword == "時間暫停" and "時間停滯" in text:
        keyword = "時間停滯"
    elif keyword == "暈眩" and "眩暈" in text:
        keyword = "眩暈"
    clauses = _effect_clauses(text, keyword)
    if not clauses:
        return ["單體"]
    return list(dict.fromkeys(_scope(clause) for clause in clauses))


def classify_ability(value: str, description: str = "") -> list[str]:
    """將原始能力依敵我方向、效果與範圍轉成可篩選的分類。"""

    text = f"{value} {description}"
    if "元素反應" in text or any(
        mechanic in text for mechanic in ELEMENTAL_MECHANICS
    ):
        return []
    results: list[str] = []
    scope_source = description or value
    for keyword, effect in _CONTROL_EFFECTS:
        if keyword in text:
            results.extend(
                f"控制-{effect}-{scope}"
                for scope in _effect_scopes(scope_source, keyword)
            )
    for keyword, prefix in _ABILITY_EFFECTS + _BENEFIT_EFFECTS:
        if keyword in text:
            if keyword == "治療" and "回復" in description:
                continue
            results.extend(
                f"{prefix}{scope}"
                for scope in _effect_scopes(scope_source, keyword)
            )
    if "驅散" in text:
        effect_text = _effect_text(scope_source, "驅散")
        prefix = (
            "減益淨化-驅散-"
            if "敵方" in effect_text
            else "增益淨化-驅散-"
        )
        results.extend(
            f"{prefix}{scope}"
            for scope in _effect_scopes(scope_source, "驅散")
        )

    if "範圍輸出" in text or "多段打擊" in text:
        keyword = "範圍輸出" if "範圍輸出" in text else "多段打擊"
        results.extend(
            f"輸出-{('範圍' if keyword == '範圍輸出' else '多段')}-{scope}"
            for scope in _effect_scopes(scope_source, keyword)
        )
    if "真實傷害" in text or "真傷" in text:
        keyword = "真實傷害" if "真實傷害" in text else "真傷"
        results.extend(
            f"輸出-真實傷害-{scope}"
            for scope in _effect_scopes(scope_source, keyword)
        )
    if "爆發" in text or "單點秒殺" in text:
        results.append("輸出-爆發-單體")
    if re.search(r"增加|提高|延長|加長", text) and "冷卻" in text:
        results.extend(
            "減益能量-加奧義冷卻-" + scope
            for scope in _effect_scopes(scope_source, "冷卻")
        )
    elif re.search(r"減少|縮短|降低|刷新|重置", text) and "冷卻" in text:
        results.extend(
            f"增益冷卻-減少-{scope}"
            for scope in _effect_scopes(scope_source, "冷卻")
        )
    if "元素反應" in text:
        results.append("元素-反應-群體")

    return list(dict.fromkeys(results))


def classify_abilities(
    values: list[str],
    description: str = "",
) -> list[str]:
    """分類多個原始標籤，並移除未分類的攻略口語。"""

    results: list[str] = []
    for value in values:
        for category in classify_ability(value, description):
            if category not in results:
                results.append(category)
    return results


_STROKE_ORDER = {
    "一": 1, "二": 2, "三": 3, "四": 5, "五": 4, "六": 4,
    "七": 2, "八": 2, "九": 2, "十": 2,
    "元": 4, "全": 6, "分": 4, "加": 5, "功": 5, "化": 4,
    "單": 12, "增": 15, "減": 12, "控": 11, "效": 10, "攻": 7,
    "族": 11, "治": 8, "消": 10, "爆": 19, "現": 11, "真": 10,
    "益": 10, "禁": 13, "群": 13, "範": 15, "輸": 16, "出": 5,
    "技": 7, "能": 10, "防": 7, "禦": 16, "療": 17, "傷": 13,
    "速": 11, "冷": 7, "卻": 7, "召": 5, "喚": 12, "分": 4,
    "免": 7, "疫": 9, "護": 21, "盾": 9, "無": 12, "敵": 15,
    "復": 12, "活": 9, "閃": 10, "避": 16, "沉": 7, "默": 16,
    "石": 5, "化": 4, "暈": 13, "眩": 10, "麻": 11, "痺": 13,
    "魅": 14, "惑": 12, "嘲": 15, "諷": 10, "擊": 17, "退": 9,
    "飛": 9, "牽": 11, "引": 4, "聚": 14, "怪": 8, "冰": 6,
    "凍": 10, "放": 8, "逐": 10, "偷": 11, "取": 8, "反": 4,
    "分": 4, "身": 7, "攻": 7, "擊": 17, "護": 21, "召": 5,
}


def stroke_sort_key(value: str) -> tuple:
    """以中文首字筆畫排序，未收錄字元以 Unicode 作穩定排序。"""

    return tuple(
        (_STROKE_ORDER.get(char, 99), ord(char))
        for char in value
    )

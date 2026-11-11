"""角色品質規則。"""


def normalize_quality(value: str) -> str:
    """將資料來源中的複合品質名稱正規化為台服三種品質。"""

    if "神話" in value:
        return "神話"
    if "傳說+" in value:
        return "傳說+"
    if "傳說" in value:
        return "傳說"
    return value


def is_legendary_or_higher(value: str) -> bool:
    """保留傳說、傳說+、限定傳說與神話等品質。"""

    return normalize_quality(value) in {"傳說", "傳說+", "神話"}

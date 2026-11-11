"""角色品質規則。"""


def is_legendary_or_higher(value: str) -> bool:
    """保留傳說、傳說+、限定傳說與神話等品質。"""

    return "傳說" in value or "神話" in value

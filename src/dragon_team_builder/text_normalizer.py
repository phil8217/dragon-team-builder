"""將外部資料中的簡體中文轉為繁體中文。"""

from opencc import OpenCC


_CONVERTER = OpenCC("s2t")


def to_traditional(value: str) -> str:
    """轉換顯示文字，保留網址與英文原文不變。"""

    return (
        _CONVERTER.convert(value)
        .replace("祕技", "秘技")
        .replace("麻痹", "麻痺")
        .replace("羣", "群")
    )

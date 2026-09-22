"""Chuẩn hoá tiếng Việt để so khớp từ vựng: bỏ dấu, thường hoá, gộp khoảng trắng."""
from __future__ import annotations

import re
import unicodedata

_WS = re.compile(r"\s+")


def strip_accents(text: str) -> str:
    # Đ/đ không phân rã được bằng NFD nên xử lý riêng.
    text = text.replace("Đ", "D").replace("đ", "d")
    nfd = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in nfd if unicodedata.category(ch) != "Mn")


def normalize(text: str) -> str:
    """'Sinh Viên  đang học' -> 'sinh vien dang hoc'."""
    text = strip_accents(text or "").lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return _WS.sub(" ", text).strip()


def split_camel(name: str) -> str:
    """'DotNhapHocSinhVien' -> 'dot nhap hoc sinh vien'."""
    return normalize(re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", name))

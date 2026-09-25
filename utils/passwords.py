"""
Băm và kiểm tra mật khẩu bằng scrypt của thư viện chuẩn Python (hashlib).

Không dùng thư viện ngoài để chạy được ngay trong container hiện tại.
Định dạng lưu: scrypt$<n>$<r>$<p>$<salt_b64>$<hash_b64>
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import string

_N, _R, _P, _DKLEN = 2 ** 15, 8, 1, 32
_MAXMEM = 64 * 1024 * 1024


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P, dklen=_DKLEN, maxmem=_MAXMEM)
    b64 = lambda b: base64.b64encode(b).decode()
    return f"scrypt${_N}${_R}${_P}${b64(salt)}${b64(dk)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, n, r, p, salt_b64, hash_b64 = stored.split("$")
        if algo != "scrypt":
            return False
        expected = base64.b64decode(hash_b64)
        dk = hashlib.scrypt(
            password.encode(), salt=base64.b64decode(salt_b64),
            n=int(n), r=int(r), p=int(p), dklen=len(expected), maxmem=_MAXMEM,
        )
        return hmac.compare_digest(dk, expected)
    except (ValueError, TypeError):
        return False


def generate_password(length: int = 16) -> str:
    """Mật khẩu ngẫu nhiên, bỏ các ký tự dễ nhầm (0/O, 1/l/I)."""
    alphabet = "".join(c for c in string.ascii_letters + string.digits if c not in "0O1lI")
    while True:
        pw = "".join(secrets.choice(alphabet) for _ in range(length))
        if any(c.islower() for c in pw) and any(c.isupper() for c in pw) and any(c.isdigit() for c in pw):
            return pw

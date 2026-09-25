"""
Tạo tài khoản quản trị cho semantic layer (bảng app_user trong Postgres nội bộ).

Bảng được tạo nếu chưa có (checkfirst), nên chạy được cả khi chưa chạy alembic.

Chạy:
    python -m scripts.create_users --seed
        Tạo bộ tài khoản mặc định còn thiếu, mật khẩu ngẫu nhiên.
    python -m scripts.create_users --username nva --full-name "Nguyễn Văn A" --role editor
        Tạo một tài khoản.
    python -m scripts.create_users --reset-password soan.daotao
        Đặt lại mật khẩu ngẫu nhiên cho một tài khoản.
    python -m scripts.create_users --list

Mật khẩu chỉ in ra một lần và ghi vào file --out (mặc định secrets/initial_accounts.txt,
quyền 600, đã nằm trong .gitignore). DB chỉ lưu bản băm.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from api.models.app_user import ROLES, AppUser
from config import get_settings
from utils.passwords import generate_password, hash_password

DEFAULT_ACCOUNTS = [
    ("admin", "Quản trị hệ thống", "admin"),
    ("duyet.daotao", "Người duyệt - Phòng Đào tạo", "approver"),
    ("duyet.nhansu", "Người duyệt - Phòng Tổ chức cán bộ", "approver"),
    ("soan.daotao", "Người soạn - Phòng Đào tạo", "editor"),
    ("soan.nhansu", "Người soạn - Phòng Tổ chức cán bộ", "editor"),
]


def _engine():
    url = (get_settings().internal_database_url
           .replace("+asyncpg", "+psycopg2").replace("ssl=disable", "sslmode=disable"))
    engine = create_engine(url)
    AppUser.__table__.create(engine, checkfirst=True)
    return engine


def _save(rows: list[tuple[str, str, str, str]], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    new_file = not out.exists()
    with out.open("a", encoding="utf-8") as f:
        if new_file:
            f.write("# Tài khoản quản trị nlsql — KHÔNG commit, đổi mật khẩu sau lần đăng nhập đầu.\n")
        f.write(f"\n## {datetime.now():%Y-%m-%d %H:%M}\n")
        for username, full_name, role, pw in rows:
            f.write(f"{username}\t{role}\t{pw}\t{full_name}\n")
    os.chmod(out, 0o600)


def _print(rows: list[tuple[str, str, str, str]]) -> None:
    print(f"{'username':<16}{'role':<10}{'password':<20}full_name")
    for username, full_name, role, pw in rows:
        print(f"{username:<16}{role:<10}{pw:<20}{full_name}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", action="store_true")
    ap.add_argument("--username")
    ap.add_argument("--full-name")
    ap.add_argument("--role", choices=ROLES)
    ap.add_argument("--reset-password", metavar="USERNAME")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--out", default="secrets/initial_accounts.txt")
    args = ap.parse_args()

    created: list[tuple[str, str, str, str]] = []
    with Session(_engine()) as s:
        if args.list:
            for u in s.scalars(select(AppUser).order_by(AppUser.role, AppUser.username)):
                print(f"{u.username:<16}{u.role:<10}{'active' if u.active else 'locked':<8}{u.full_name}")
            return 0

        if args.reset_password:
            u = s.scalar(select(AppUser).where(AppUser.username == args.reset_password))
            if not u:
                print(f"Không có tài khoản {args.reset_password}", file=sys.stderr)
                return 1
            pw = generate_password()
            u.password_hash, u.must_change_password = hash_password(pw), True
            created.append((u.username, u.full_name, u.role, pw))
        else:
            wanted = list(DEFAULT_ACCOUNTS) if args.seed else []
            if args.username:
                if not (args.full_name and args.role):
                    ap.error("--username cần kèm --full-name và --role")
                wanted.append((args.username, args.full_name, args.role))
            if not wanted:
                ap.error("chọn --seed, --username, --reset-password hoặc --list")
            existing = set(s.scalars(select(AppUser.username)))
            for username, full_name, role in wanted:
                if username in existing:
                    print(f"Bỏ qua {username}: đã tồn tại")
                    continue
                pw = generate_password()
                s.add(AppUser(username=username, full_name=full_name, role=role,
                              password_hash=hash_password(pw)))
                created.append((username, full_name, role, pw))
        s.commit()

    if created:
        _print(created)
        _save(created, Path(args.out))
        print(f"\nĐã ghi mật khẩu vào {args.out} (chmod 600).")
    return 0


if __name__ == "__main__":
    sys.exit(main())

import argparse
import sqlite3
from pathlib import Path


def verify_backup(path: Path) -> None:
    path = path.resolve()

    if not path.is_file():
        raise FileNotFoundError(f"备份文件不存在：{path}")

    connection = sqlite3.connect(
        path.as_uri() + "?mode=ro",
        uri=True,
    )

    try:
        integrity = connection.execute(
            "PRAGMA integrity_check"
        ).fetchall()

        if integrity != [("ok",)]:
            raise RuntimeError(f"完整性检查失败：{integrity}")

        violations = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        if violations:
            raise RuntimeError(f"外键检查失败：{violations}")

        user_count = connection.execute(
            "SELECT COUNT(*) FROM users"
        ).fetchone()[0]

        transaction_count = connection.execute(
            "SELECT COUNT(*) FROM transactions"
        ).fetchone()[0]

        revisions = connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchall()

        print("完整性检查：通过")
        print("外键检查：通过")
        print(f"用户数量：{user_count}")
        print(f"账单数量：{transaction_count}")
        print(f"迁移版本：{revisions}")
    finally:
        connection.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    args = parser.parse_args()

    verify_backup(args.path)
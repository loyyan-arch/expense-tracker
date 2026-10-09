import sqlite3
from datetime import datetime

from db import DB_PATH


if __name__ == "__main__":
    if not DB_PATH.is_file():
        raise RuntimeError("数据库文件不存在")

    backup_dir = DB_PATH.parent / "backups"
    backup_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    backup_path = backup_dir / f"expenses_{timestamp}.db"

    source = sqlite3.connect(
        DB_PATH.as_uri() + "?mode=ro",
        uri=True,
    )
    destination = sqlite3.connect(backup_path)

    try:
        source.backup(destination)
        result = destination.execute(
            "PRAGMA integrity_check"
        ).fetchone()

        if result != ("ok",):
            raise RuntimeError(f"备份完整性检查失败：{result}")
    finally:
        destination.close()
        source.close()

    print(f"备份完成：{backup_path}")
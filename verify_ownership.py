import sqlite3

from db import DB_PATH


if __name__ == "__main__":
    connection = sqlite3.connect(
        DB_PATH.as_uri() + "?mode=ro",
        uri=True,
    )

    try:
        rows = connection.execute(
            """
            SELECT users.username, COUNT(*)
            FROM transactions
            LEFT JOIN users ON transactions.user_id = users.id
            GROUP BY users.username
            """
        ).fetchall()

        violations = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        print("账单归属统计：", rows)
        print("外键违规记录：", violations)
    finally:
        connection.close()
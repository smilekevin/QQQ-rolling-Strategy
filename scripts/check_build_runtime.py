"""下载前验证 yfinance 使用的 Peewee SQLite 缓存驱动。"""
import sys

import peewee


def main():
    database = peewee.SqliteDatabase(":memory:")
    try:
        with database.connection_context():
            database.execute_sql("CREATE TABLE runtime_check (value INTEGER)")
            database.execute_sql("INSERT INTO runtime_check VALUES (1)")
            if database.execute_sql("SELECT value FROM runtime_check").fetchone() != (1,):
                raise RuntimeError("SQLite 缓存读写自检失败")
    except peewee.ImproperlyConfigured as error:
        raise SystemExit(
            "SQLite 缓存驱动不可用；Cloudflare Linux x86_64 构建需安装 "
            "requirements.txt 中的 pysqlite3-binary。"
        ) from error
    print(
        f"构建环境自检通过：Python {sys.version.split()[0]}；"
        f"SQLite {peewee.sqlite3.sqlite_version}（{peewee.sqlite3.__name__}）",
        flush=True,
    )


if __name__ == "__main__":
    main()

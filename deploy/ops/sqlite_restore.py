import os
import shutil
import sqlite3
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: sqlite_restore.py BACKUP TARGET", file=sys.stderr)
        return 2

    backup = Path(sys.argv[1]).resolve()
    target = Path(sys.argv[2]).resolve()
    if not backup.is_file():
        print(f"SQLite backup does not exist: {backup}", file=sys.stderr)
        return 2
    if backup == target or target == Path("/"):
        print("Unsafe SQLite restore target.", file=sys.stderr)
        return 2

    with sqlite3.connect(f"file:{backup}?mode=ro", uri=True) as backup_db:
        integrity = backup_db.execute("PRAGMA integrity_check").fetchone()
    if integrity != ("ok",):
        print("Refusing to restore a corrupt SQLite backup.", file=sys.stderr)
        return 1

    target.parent.mkdir(parents=True, exist_ok=True)
    temporary_target = target.with_name(f".{target.name}.restore-{os.getpid()}")
    shutil.copy2(backup, temporary_target)
    os.replace(temporary_target, target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

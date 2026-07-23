import sqlite3
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: sqlite_backup.py SOURCE TARGET", file=sys.stderr)
        return 2

    source = Path(sys.argv[1]).resolve()
    target = Path(sys.argv[2]).resolve()
    if not source.is_file():
        print(f"SQLite source does not exist: {source}", file=sys.stderr)
        return 2
    if source == target:
        print("Source and target must be different.", file=sys.stderr)
        return 2

    target.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(f"file:{source}?mode=ro", uri=True) as source_db:
        with sqlite3.connect(target) as target_db:
            source_db.backup(target_db)
            integrity = target_db.execute("PRAGMA integrity_check").fetchone()

    if integrity != ("ok",):
        target.unlink(missing_ok=True)
        print("SQLite backup failed its integrity check.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

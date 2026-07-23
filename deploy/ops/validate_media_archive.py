import sys
import tarfile
from pathlib import PurePosixPath


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_media_archive.py ARCHIVE", file=sys.stderr)
        return 2

    archive_path = sys.argv[1]
    try:
        with tarfile.open(archive_path, mode="r:gz") as archive:
            for member in archive.getmembers():
                member_path = PurePosixPath(member.name)
                if (
                    member_path.is_absolute()
                    or ".." in member_path.parts
                    or member.issym()
                    or member.islnk()
                    or not (member.isfile() or member.isdir())
                ):
                    print(
                        f"Unsafe media archive member: {member.name}",
                        file=sys.stderr,
                    )
                    return 1
    except (OSError, tarfile.TarError) as exc:
        print(f"Invalid media archive: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

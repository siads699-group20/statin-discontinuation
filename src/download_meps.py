"""Download the MEPS ZIP files listed in README.md."""

from __future__ import annotations

import re
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCES_PATH = ROOT / "README.md"
RAW_DIR = ROOT / "data" / "raw"
SOURCE_ROW = re.compile(r"^\| `([^`]+\.zip)` \|.*?<((?:https?://)[^>]+)> \|")


def read_sources() -> list[tuple[str, str]]:
    sources = []
    for line in SOURCES_PATH.read_text(encoding="utf-8").splitlines():
        match = SOURCE_ROW.match(line)
        if match:
            filename, url = match.groups()
            if Path(filename).name != filename:
                raise ValueError(f"Invalid filename: {filename}")
            sources.append((filename, url))

    if not sources:
        raise ValueError(f"No ZIP sources found")
    return sources


def is_valid_zip(path: Path) -> bool:
    try:
        with zipfile.ZipFile(path) as archive:
            return archive.testzip() is None
    except (OSError, zipfile.BadZipFile):
        return False


def download_file(url: str, dest: Path) -> None:
    tmp: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=dest.parent, prefix=f".{dest.name}.", suffix=".part",
            delete=False,
        ) as temporary_file:
            tmp = Path(temporary_file.name)
            request = urllib.request.Request(
                url, headers={"User-Agent": "statin-discontinuation-data-pipeline"}
            )
            with urllib.request.urlopen(request, timeout=60) as response:
                while chunk := response.read(1024 * 1024):
                    temporary_file.write(chunk)

        if not is_valid_zip(tmp):
            raise ValueError(f"Downloaded file ivalid: {tmp}")
        tmp.replace(dest)
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)


def main() -> int:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for filename, url in read_sources():
        dest = RAW_DIR / filename
        if dest.exists():
            if is_valid_zip(dest):
                print(f"Already downloaded and valid: {dest.relative_to(ROOT)}")
                continue
            raise ValueError(f"retrying: {dest}")

        print(f"Downloading {filename} from {url}")
        try:
            download_file(url, dest)
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            print(f"Failed to download {filename}: {exc}", file=sys.stderr)
            return 1
        print(f"Saved {dest.relative_to(ROOT)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""
MIT License

Copyright (c) 2025 VeloSim Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from __future__ import annotations

import tarfile
from pathlib import Path

from grafana_logging.logger import get_logger

logger = get_logger(__name__)

DATASETS_DIR = Path("sim/traffic/traffic_datasets")
ARCHIVE_PATH = DATASETS_DIR / "traffic.tar.gz"
EXPECTED_FILES = [
    "default.csv",
    "high_congestion.csv",
    "medium_congestion.csv",
    "low_congestion.csv",
]


def extract_templates() -> int:
    """Extract packaged traffic template CSVs from local archive.

    Returns:
        Exit status code (0 success, 1 failure).
    """
    if not ARCHIVE_PATH.exists():
        logger.error("Traffic template archive not found at %s", ARCHIVE_PATH)
        return 1

    try:
        DATASETS_DIR.mkdir(parents=True, exist_ok=True)
        with tarfile.open(ARCHIVE_PATH, "r:gz") as tar:
            members = {Path(m.name).name: m for m in tar.getmembers() if m.isfile()}
            missing = [name for name in EXPECTED_FILES if name not in members]
            if missing:
                logger.error(
                    "Archive is missing expected template files: %s", ", ".join(missing)
                )
                return 1

            for filename in EXPECTED_FILES:
                member = members[filename]
                # Extract to temp then atomically move into place.
                tmp_path = DATASETS_DIR / f"{filename}.tmp"
                out_path = DATASETS_DIR / filename
                try:
                    src = tar.extractfile(member)
                    if src is None:
                        logger.error("Failed reading %s from archive", filename)
                        return 1
                    with src:
                        tmp_path.write_bytes(src.read())
                    tmp_path.replace(out_path)
                    logger.info("Prepared traffic template: %s", out_path)
                except Exception as exc:
                    logger.error("Failed extracting %s: %s", filename, exc)
                    if tmp_path.exists():
                        tmp_path.unlink()
                    return 1

        return 0
    except Exception as exc:  # pragma: no cover - defensive logging path
        logger.error("Failed to extract traffic templates: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(extract_templates())

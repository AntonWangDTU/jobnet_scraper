"""One-time script to backfill job IDs into existing reports."""

import hashlib
import re
from pathlib import Path

REPORTS_DIR = Path(__file__).parent / "reports"
JOBNET_RE = re.compile(r"https://jobnet\.dk/find-job/([a-f0-9\-]{36})")


def id_from_url(url: str) -> str:
    m = JOBNET_RE.search(url)
    if m:
        return m.group(1)
    # Stable hash for external URLs
    return "ext-" + hashlib.md5(url.encode()).hexdigest()[:12]


def backfill(path: Path) -> int:
    lines = path.read_text().splitlines()
    new_lines = []
    changed = 0

    i = 0
    while i < len(lines):
        line = lines[i]
        # Check if this is a URL line without a preceding ID line
        if line.startswith("- **URL:**"):
            prev = new_lines[-1] if new_lines else ""
            if not prev.startswith("- **ID:**"):
                url = line.split("- **URL:**", 1)[1].strip()
                job_id = id_from_url(url)
                new_lines.append(f"- **ID:** {job_id}")
                changed += 1
        new_lines.append(line)
        i += 1

    if changed:
        path.write_text("\n".join(new_lines))
        print(f"  {path.name}: inserted {changed} ID(s)")
    else:
        print(f"  {path.name}: already up to date")

    return changed


if __name__ == "__main__":
    reports = sorted(REPORTS_DIR.glob("*.md"))
    if not reports:
        print("No reports found.")
    else:
        total = 0
        for report in reports:
            total += backfill(report)
        print(f"\nDone. {total} ID(s) inserted across {len(reports)} report(s).")

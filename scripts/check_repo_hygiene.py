from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def tracked_files() -> list[str]:
    proc = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
    )
    return [p.decode("utf-8") for p in proc.stdout.split(b"\0") if p]


def main() -> int:
    files = tracked_files()
    violations: list[str] = []

    for path in files:
        low = path.lower()
        if low.endswith((".jar", ".class")):
            violations.append(f"binary client/JVM artifact is tracked: {path}")
        if low.startswith(("decompiled/", "recovered-src/")):
            violations.append(f"generated/recovered source is tracked: {path}")
        if low.startswith("evidence/binaries/") and not low.endswith("/.gitkeep"):
            violations.append(f"binary evidence is tracked: {path}")
        if low.startswith("generated/") and not low.endswith("/.gitkeep"):
            violations.append(f"generated artifact is tracked: {path}")

    json_roots = [ROOT / "authority", ROOT / "mappings", ROOT / "schemas"]
    for base in json_roots:
        if not base.exists():
            continue
        for path in sorted(base.rglob("*.json")):
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:
                violations.append(f"invalid JSON {path.relative_to(ROOT)}: {exc}")

    if violations:
        print("SPK_REPO_HYGIENE_FAIL", file=sys.stderr)
        for violation in violations:
            print(f"- {violation}", file=sys.stderr)
        return 1

    print("SPK_REPO_HYGIENE_PASS")
    print(f"tracked_files={len(files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

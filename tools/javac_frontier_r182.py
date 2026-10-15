"""Read-only, fail-closed javac diagnostic frontier (R182).

Input is an existing -XDrawDiagnostics transcript. This tool does not compile
private files, evaluate original client code, or accept binary fallbacks.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

# -XDrawDiagnostics examples:
# Foo.java:7:9: compiler.err.cant.resolve.location: ...
# Foo.java:7: compiler.err.doesnt.exist: ...
_DIAG = re.compile(
    r"^(?P<file>.*?\.java):(?P<line>\d+):(?:(?P<column>\d+):)? "
    r"(?P<key>compiler\.(?:err|warn|note)\.[\w.]+)(?:: (?P<message>.*))?$"
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_transcript(lines: list[str]) -> tuple[list[dict], list[str]]:
    records, unparsed = [], []
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        match = _DIAG.fullmatch(line)
        if match:
            entry = match.groupdict()
            entry["line"] = int(entry["line"])
            entry["column"] = int(entry["column"]) if entry["column"] else None
            entry["message"] = entry["message"] or ""
            # An error code does not establish whether its root cause is a
            # missing third-party library, unrecovered class, or alias collision.
            entry["root_cause"] = "unknown"
            entry["confidence"] = "unclassified"
            records.append(entry)
        elif not re.fullmatch(r"\d+ (?:errors?|warnings?)", line):
            unparsed.append(line)
    return records, unparsed


def build_report(path: Path, expected_sha: str, profile: str) -> dict:
    actual = sha256(path)
    if actual.lower() != expected_sha.lower():
        raise ValueError("Transcript SHA-256 mismatch; refusing unpinned input")
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", profile):
        raise ValueError("Invalid profile identifier")
    rows, unparsed = parse_transcript(path.read_text(encoding="utf-8").splitlines())
    rows.sort(key=lambda r: (r["file"].casefold(), r["file"], r["line"],
                             r["column"] or 0, r["key"], r["message"]))
    return {
        "schema": "spk.javac-frontier.r182.v1",
        "profile": profile,
        "transcript_sha256": actual,
        "parsed_diagnostic_count": len(rows),
        "unparsed_line_count": len(unparsed),
        "root_cause_status": "not_proven",
        "diagnostics": rows,
        "unparsed_lines": unparsed,
        "limitations": [
            "Transcript ingestion only; no compilation performed",
            "Original raw javac count not independently verified",
            "No dependency provenance or source tree was examined",
            "Root causes remain unknown until separately evidenced",
            "Do not compare error counts across different profiles",
        ],
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("transcript", type=Path)
    p.add_argument("--sha256", required=True, help="Expected SHA-256 of transcript")
    p.add_argument("--profile", required=True, help="Immutable build profile identifier")
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    report = build_report(args.transcript, args.sha256, args.profile)
    # Fail closed: never overwrite prior results.
    with args.output.open("x", encoding="utf-8", newline="\n") as out:
        json.dump(report, out, indent=2, sort_keys=True, ensure_ascii=True)
        out.write("\n")


if __name__ == "__main__":
    main()

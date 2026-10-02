from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .bytecode_profile import BytecodeProfileError, profile_jar_class


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _stable_id(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest().upper()[:20]


def build_report(
    jar_path: Path,
    entry_path: str,
    method_name: str,
    descriptor: str,
) -> dict[str, Any]:
    if not jar_path.is_file():
        raise BytecodeProfileError(f"JAR does not exist: {jar_path}")
    if (
        not entry_path.endswith(".class")
        or entry_path.startswith("/")
        or "\\" in entry_path
        or ".." in Path(entry_path).parts
    ):
        raise BytecodeProfileError(
            f"invalid class entry path: {entry_path}"
        )

    profile = profile_jar_class(jar_path, entry_path)
    methods = [
        row
        for row in profile.get("methods", [])
        if row.get("name") == method_name
        and row.get("descriptor") == descriptor
    ]
    if len(methods) != 1:
        raise BytecodeProfileError(
            "expected exactly one exact method match: "
            f"{entry_path} {method_name}{descriptor}; found={len(methods)}"
        )

    method = methods[0]
    core = {
        "jar_sha256": _sha256(jar_path),
        "entry_path": entry_path,
        "internal_name": profile.get("internal_name"),
        "method_name": method_name,
        "method_descriptor": descriptor,
        "access": method.get("access"),
        "code_length": method.get("code_length"),
        "instructions": method.get("instructions", []),
        "field_accesses": method.get("field_accesses", []),
        "method_invocations": method.get("method_invocations", []),
    }
    return {
        "schema_version": 1,
        "probe_id": "BYTECODEMETHOD_" + _stable_id(core),
        **core,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Emit a deterministic exact JVM instruction profile for one "
            "class method."
        )
    )
    parser.add_argument("jar", type=Path)
    parser.add_argument("entry")
    parser.add_argument("method")
    parser.add_argument("descriptor")
    parser.add_argument("--out", type=Path)
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        report = build_report(
            args.jar,
            args.entry,
            args.method,
            args.descriptor,
        )
    except (BytecodeProfileError, OSError, KeyError) as exc:
        raise SystemExit(str(exc)) from exc

    encoded = json.dumps(
        report,
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    )
    if args.out is None:
        print(encoded)
    else:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(encoded + "\n", encoding="utf-8")
        print(f"probe_id={report['probe_id']}")
        print(f"out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

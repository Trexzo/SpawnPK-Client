from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any
import zipfile

from .external_source_oracle import EXACT_V308_SHA256
from .indexer import sha256_file


class ExternalOracleDependencyCapsuleError(ValueError):
    pass


def _stable_digest(value: Any) -> str:
    raw = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def build_nonproject_dependency_capsule(
    *,
    exact_v308_jar: Path,
    out_jar: Path,
    expected_v308_sha256: str = EXACT_V308_SHA256,
) -> dict[str, Any]:
    exact_v308_jar = exact_v308_jar.resolve()
    out_jar = out_jar.resolve()
    expected_v308_sha256 = expected_v308_sha256.strip().lower()

    if not exact_v308_jar.is_file():
        raise ExternalOracleDependencyCapsuleError(
            f"exact v308 JAR is missing: {exact_v308_jar}"
        )
    actual_sha = sha256_file(exact_v308_jar)
    if actual_sha != expected_v308_sha256:
        raise ExternalOracleDependencyCapsuleError(
            "exact-v308 SHA-256 mismatch: "
            f"expected={expected_v308_sha256} actual={actual_sha}"
        )
    if out_jar == exact_v308_jar:
        raise ExternalOracleDependencyCapsuleError(
            "dependency capsule output may not replace exact v308"
        )

    selected: list[tuple[str, bytes]] = []
    duplicate_names: set[str] = set()
    seen: set[str] = set()
    rs_entry_count = 0

    with zipfile.ZipFile(exact_v308_jar, "r") as source:
        for info in source.infolist():
            name = info.filename
            if name in seen:
                duplicate_names.add(name)
            seen.add(name)
            if info.is_dir():
                continue
            if name.startswith("rs/"):
                rs_entry_count += 1
                continue
            if not name.endswith(".class"):
                continue
            selected.append((name, source.read(info)))

    if duplicate_names:
        first = sorted(duplicate_names)[0]
        raise ExternalOracleDependencyCapsuleError(
            f"exact v308 contains duplicate ZIP entry: {first}"
        )
    if not selected:
        raise ExternalOracleDependencyCapsuleError(
            "no non-rs class dependencies selected"
        )

    out_jar.parent.mkdir(parents=True, exist_ok=True)
    if out_jar.exists():
        out_jar.unlink()

    with zipfile.ZipFile(
        out_jar,
        "w",
        compression=zipfile.ZIP_STORED,
    ) as target:
        for name, data in sorted(selected):
            info = zipfile.ZipInfo(
                filename=name,
                date_time=(1980, 1, 1, 0, 0, 0),
            )
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 0
            info.external_attr = 0
            target.writestr(info, data)

    with zipfile.ZipFile(out_jar, "r") as check:
        names = [
            info.filename
            for info in check.infolist()
            if not info.is_dir()
        ]
        unexpected_rs = [
            name for name in names if name.startswith("rs/")
        ]
        if unexpected_rs:
            raise ExternalOracleDependencyCapsuleError(
                "generated dependency capsule contains rs/** entries"
            )
        class_count = sum(
            1 for name in names if name.endswith(".class")
        )

    material = {
        "source_v308_sha256": actual_sha,
        "capsule_sha256": sha256_file(out_jar),
        "class_count": class_count,
        "rs_class_count": 0,
        "excluded_rs_entry_count": rs_entry_count,
    }
    capsule_id = (
        "EXTDEPS_"
        + _stable_digest(material)[:20].upper()
    )
    return {
        "schema_version": 1,
        "kind": "external_oracle_dependency_capsule",
        "capsule_id": capsule_id,
        **material,
        "project_binary_fallback_count": 0,
        "scope": "non-rs-classfiles-only",
    }


def _print_human(report: dict[str, Any]) -> None:
    print("SPK_EXTERNAL_ORACLE_DEPENDENCY_CAPSULE_PASS")
    print(f"capsule_id={report['capsule_id']}")
    print(
        "source_v308_sha256="
        f"{report['source_v308_sha256']}"
    )
    print(
        "capsule_sha256="
        f"{report['capsule_sha256']}"
    )
    print(f"class_count={report['class_count']}")
    print("rs_class_count=0")
    print("project_binary_fallback_count=0")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build a compile-only exact-v308 dependency capsule "
            "with every rs/** entry removed."
        )
    )
    parser.add_argument("exact_v308_jar", type=Path)
    parser.add_argument("out_jar", type=Path)
    parser.add_argument(
        "--expected-v308-sha256",
        default=EXACT_V308_SHA256,
    )
    parser.add_argument("--report-out", type=Path)
    args = parser.parse_args(argv)

    report = build_nonproject_dependency_capsule(
        exact_v308_jar=args.exact_v308_jar,
        out_jar=args.out_jar,
        expected_v308_sha256=args.expected_v308_sha256,
    )
    if args.report_out is not None:
        args.report_out.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        args.report_out.write_text(
            json.dumps(
                report,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"report_out={args.report_out}")
    _print_human(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

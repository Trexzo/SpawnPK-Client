"""Run two independently pinned JVM decompilers on one exact original class slice.

Generated Java and the original class slice are intentionally private. This
module does not accept source, class or member identity into canonical lineage.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from .decompiler import DecompilerError, run_decompiler
from .exact_class_slice import ClassSliceError, build_class_slice


class DualDecompilerError(ValueError):
    """Unsafe, missing or inconsistent original/decompiler input."""


def _require(ok: bool, message: str) -> None:
    if not ok:
        raise DualDecompilerError(message)


def _digest_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _verify_input(path: Path, sha256: str, kind: str) -> str:
    _require(
        isinstance(sha256, str) and re.fullmatch(r"[0-9a-fA-F]{64}", sha256) is not None,
        f"INVALID_{kind}_SHA256_PIN",
    )
    _require(path.is_file(), f"{kind}_FILE_MISSING")
    actual = _digest_file(path)
    _require(actual.lower() == sha256.lower(), f"{kind}_SHA256_MISMATCH")
    return actual


def _java_tree_digest(root: Path) -> tuple[str, int]:
    """Tree fingerprint without disclosing source, paths or class coordinates."""
    _require(root.is_dir(), "DECOMPILER_OUTPUT_DIRECTORY_MISSING")
    entries = sorted(root.rglob("*.java"), key=lambda path: path.relative_to(root).as_posix())
    _require(bool(entries), "DECOMPILER_OUTPUT_HAS_NO_JAVA")
    h = hashlib.sha256()
    for path in entries:
        _require(path.is_file() and not path.is_symlink(), "UNSAFE_GENERATED_JAVA_FILE")
        relative = path.relative_to(root).as_posix().encode("utf-8")
        _require(b"\x00" not in relative, "INVALID_GENERATED_SOURCE_PATH")
        h.update(len(relative).to_bytes(8, "big"))
        h.update(relative)
        with path.open("rb") as source:
            file_hash = hashlib.sha256()
            for part in iter(lambda: source.read(1024 * 1024), b""):
                file_hash.update(part)
            h.update(file_hash.digest())
    return h.hexdigest(), len(entries)


def run_targeted_dual_decompilation(
    original_jar: Path, cfr_jar: Path, vineflower_jar: Path, out_root: Path,
    *, original_sha256: str, cfr_sha256: str, vineflower_sha256: str,
    class_entry: str, java_command: str = "java",
    timeout_seconds: int = 300,
) -> dict[str, Any]:
    """Preflight all three complete JAR pins before creating any output.

    The output root must not exist. Original and tools remain unmodified.
    Partial *private* outputs are preserved if an engine fails, but no success
    report is written unless both engines finish and postflight passes.
    """
    original_jar = Path(original_jar).resolve()
    cfr_jar = Path(cfr_jar).resolve()
    vineflower_jar = Path(vineflower_jar).resolve()
    out_root = Path(out_root).resolve()

    # The dual-decompiler workflow is intentionally bounded by default.
    # Validate before even reading input archives or creating private output.
    _require(
        type(timeout_seconds) is int and 1 <= timeout_seconds <= 3600,
        "INVALID_DUAL_DECOMPILER_TIMEOUT",
    )

    exact_pins = {
        "ORIGINAL": _verify_input(original_jar, original_sha256, "ORIGINAL"),
        "CFR": _verify_input(cfr_jar, cfr_sha256, "CFR"),
        "VINEFLOWER": _verify_input(vineflower_jar, vineflower_sha256, "VINEFLOWER"),
    }
    _require(len({original_jar, cfr_jar, vineflower_jar}) == 3,
             "ORIGINAL_AND_DECOMPILER_INPUTS_MUST_BE_SEPARATE")
    _require(not out_root.exists(), "OUTPUT_ROOT_ALREADY_EXISTS")
    out_root.parent.mkdir(parents=True, exist_ok=True)
    try:
        out_root.mkdir()
    except FileExistsError as exc:
        raise DualDecompilerError("OUTPUT_ROOT_ALREADY_EXISTS") from exc

    slice_path = out_root / "exact-private-slice.jar"
    try:
        slice_report = build_class_slice(
            original_jar, slice_path,
            original_sha256=exact_pins["ORIGINAL"], class_entry=class_entry,
            include_nested=True,
        )
        engines: dict[str, dict[str, Any]] = {}
        for engine, tool_path, pin_key in (
            ("cfr", cfr_jar, "CFR"),
            ("vineflower", vineflower_jar, "VINEFLOWER"),
        ):
            dest = out_root / engine
            output = run_decompiler(
                slice_path, tool_path,
                expected_decompiler_sha256=exact_pins[pin_key],
                engine=engine,
                out_dir=dest,
                clean_out=False,
                java_command=java_command,
                timeout_seconds=timeout_seconds,
            )
            tree_sha, file_count = _java_tree_digest(dest)
            _require(file_count == output["java_file_count"],
                     "DECOMPILER_JAVA_FILE_COUNT_DRIFT")
            engines[engine] = {
                "tool_sha256": exact_pins[pin_key],
                "java_file_count": file_count,
                "java_tree_sha256": tree_sha,
            }

        _require(_digest_file(slice_path) == slice_report["slice_sha256"],
                 "PRIVATE_SLICE_CHANGED")
        for kind, path in (
            ("ORIGINAL", original_jar),
            ("CFR", cfr_jar),
            ("VINEFLOWER", vineflower_jar),
        ):
            _require(_digest_file(path) == exact_pins[kind],
                     f"{kind}_CHANGED_DURING_EXECUTION")
        core = {
            "schema_version": 1,
            "kind": "private_dual_decompiler_research",
            "research_only": True,
            "canonical_identity_accepted": False,
            "source_equivalence_certified": False,
            "original_jar_sha256": exact_pins["ORIGINAL"],
            "private_slice_sha256": slice_report["slice_sha256"],
            "included_class_count": slice_report["included_class_count"],
            "engines_executed": 2,
            "timeout_seconds_per_engine": timeout_seconds,
            "engines": engines,
        }
        fingerprint = hashlib.sha256(json.dumps(
            core, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        ).encode("utf-8")).hexdigest().upper()[:20]
        result = {"report_id": "DUALDECOMP_" + fingerprint, **core}
        with (out_root / "private-research-manifest.json").open(
            "x", encoding="utf-8", newline="\n",
        ) as stream:
            json.dump(result, stream, indent=2, sort_keys=True, ensure_ascii=False)
            stream.write("\n")
        return result
    except (ClassSliceError, DecompilerError, OSError):
        # Existing decompiler exceptions include subprocess stdout/stderr,
        # which can reveal private class paths, members or generated source.
        # This public-facing CLI must never echo those details.
        raise DualDecompilerError("PRIVATE_DUAL_DECOMPILATION_FAILED") from None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original_jar", type=Path)
    parser.add_argument("cfr_jar", type=Path)
    parser.add_argument("vineflower_jar", type=Path)
    parser.add_argument("out_root", type=Path)
    parser.add_argument("--class-entry", required=True)
    parser.add_argument("--original-sha256", required=True)
    parser.add_argument("--cfr-sha256", required=True)
    parser.add_argument("--vineflower-sha256", required=True)
    parser.add_argument("--java-command", default="java")
    parser.add_argument("--timeout-seconds", type=int, default=300,
                        help="1-3600 seconds per engine (default: 300)")
    args = parser.parse_args(argv)
    try:
        result = run_targeted_dual_decompilation(
            args.original_jar, args.cfr_jar, args.vineflower_jar, args.out_root,
            original_sha256=args.original_sha256,
            cfr_sha256=args.cfr_sha256,
            vineflower_sha256=args.vineflower_sha256,
            class_entry=args.class_entry,
            java_command=args.java_command,
            timeout_seconds=args.timeout_seconds,
        )
        # Never print generated source or class coordinates in a success report.
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (DualDecompilerError, ValueError, OSError) as exc:
        parser.error(str(exc))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

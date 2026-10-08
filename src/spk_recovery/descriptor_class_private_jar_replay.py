from __future__ import annotations

"""Fail-closed local exact-JAR replay; only the small research result is written.

No JAR or full private index is copied to GitHub or the requested output path.
This command never mutates tracked canonical class/member lineage.
"""

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .descriptor_class_verified_replay import build_descriptor_class_verified_replay
from .indexer import index_jar, sha256_file


class ExactJarDescriptorClassReplayError(ValueError):
    pass


def _sha256(path: Path) -> str:
    return sha256_file(path).lower()


def _read_json_exact(path: Path) -> dict[str, Any]:
    def no_duplicate_keys(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ExactJarDescriptorClassReplayError(
                    f"duplicate JSON key in {path}: {key}"
                )
            result[key] = value
        return result

    data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=no_duplicate_keys)
    if not isinstance(data, dict):
        raise ExactJarDescriptorClassReplayError(f"{path}: expected JSON object")
    return data


def build_exact_jar_descriptor_class_replay(
    old_jar: Path,
    new_jar: Path,
    frontier_path: Path,
    class_lineage_path: Path,
    global_field_report_path: Path,
) -> dict[str, Any]:
    """Verify the accepted frontier and exact local JARs before any evidence replay."""
    frontier = _read_json_exact(frontier_path)
    if (
        frontier.get("kind") != "v309_recovery_frontier"
        or frontier.get("state") != "ACCEPTED_INCOMPLETE"
        or frontier.get("build_id") != "v309"
        or frontier.get("frontier", {}).get("unresolved") != 143
    ):
        raise ExactJarDescriptorClassReplayError(
            "expected pinned accepted incomplete 143-field v309 frontier"
        )

    exact = frontier.get("exact_clients", {})
    file_proofs = frontier.get("files", {})
    for name, path in (
        ("class_lineage", class_lineage_path),
        ("global_field_usage", global_field_report_path),
    ):
        expected = file_proofs.get(name, {}).get("sha256")
        if (
            not isinstance(expected, str)
            or len(expected) != 64
            or _sha256(path) != expected.lower()
        ):
            raise ExactJarDescriptorClassReplayError(
                f"tracked {name} SHA-256 differs from accepted frontier"
            )

    for name, path in (("v308", old_jar), ("v309", new_jar)):
        expected = exact.get(name + "_sha256")
        if (
            not isinstance(expected, str)
            or len(expected) != 64
            or _sha256(path) != expected.lower()
        ):
            raise ExactJarDescriptorClassReplayError(
                f"{name} exact client SHA-256 mismatch"
            )

    lineage = _read_json_exact(class_lineage_path)
    global_report = _read_json_exact(global_field_report_path)
    if (
        global_report.get("old_sha256", "").lower() != exact["v308_sha256"].lower()
        or global_report.get("new_sha256", "").lower() != exact["v309_sha256"].lower()
        or global_report.get("report_id") != file_proofs["global_field_usage"].get("report_id")
    ):
        raise ExactJarDescriptorClassReplayError(
            "global report build hashes or report ID do not match pinned frontier"
        )

    old_index = index_jar(old_jar)
    new_index = index_jar(new_jar)
    for name, index in (("v308", old_index), ("v309", new_index)):
        if index.get("summary", {}).get("class_parse_error_count") != 0:
            raise ExactJarDescriptorClassReplayError(
                f"{name} index contains unparsed classes"
            )
        if index.get("sha256", "").lower() != exact[name + "_sha256"].lower():
            raise ExactJarDescriptorClassReplayError(
                f"{name} JAR changed between preflight and indexing"
            )

    result = build_descriptor_class_verified_replay(
        global_report, lineage, old_index, new_index
    )
    if result.get("canonical") is not False or result.get("state") != "NO_CLASS_OR_MEMBER_IDENTITY_ACCEPTED":
        raise ExactJarDescriptorClassReplayError("research-only replay safety violation")
    if (
        result["summary"]["candidate_fields_blocked"]
        + result["summary"]["still_blocked_fields"] != 26
        or result["summary"]["input_class_dependencies"] != 8
    ):
        raise ExactJarDescriptorClassReplayError(
            "class dependency accounting changed from pinned 26/8 frontier"
        )
    return result


def write_research_report_no_clobber(
    report: dict[str, Any],
    out_path: Path,
    protected_inputs: tuple[Path, ...],
) -> None:
    """Write only a new research file; never overwrite a pinned input or prior result."""
    resolved_out = out_path.resolve()
    if any(resolved_out == path.resolve() for path in protected_inputs):
        raise ExactJarDescriptorClassReplayError(
            "research output must not overwrite a pinned JAR or frontier input"
        )
    if out_path.exists() or out_path.is_symlink():
        raise ExactJarDescriptorClassReplayError(
            "research output already exists; choose a new path"
        )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(
            json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
        )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="spk-v309-exact-jar-class-replay",
        description="Research-only v309 class witness replay from pinned private JARs",
    )
    p.add_argument("--v308-jar", type=Path, required=True)
    p.add_argument("--v309-jar", type=Path, required=True)
    p.add_argument(
        "--frontier", type=Path,
        default=Path("research/v309-field-recovery/frontier.json"),
    )
    p.add_argument(
        "--class-lineage", type=Path,
        default=Path("research/v309-field-recovery/class-lineage.json"),
    )
    p.add_argument(
        "--global-field-report", type=Path,
        default=Path("research/v309-field-recovery/global-field-usage.json"),
    )
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args(argv)
    try:
        report = build_exact_jar_descriptor_class_replay(
            args.v308_jar, args.v309_jar,
            args.frontier, args.class_lineage, args.global_field_report,
        )
        write_research_report_no_clobber(
            report, args.out, (
                args.v308_jar, args.v309_jar,
                args.frontier, args.class_lineage, args.global_field_report,
            )
        )
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print(f"SPK_V309_EXACT_JAR_CLASS_REPLAY_FAIL: {exc}")
        return 1
    print("SPK_V309_EXACT_JAR_CLASS_REPLAY_PASS_RESEARCH_ONLY")
    print(f"report_id={report['report_id']}")
    for key, value in report["summary"].items():
        print(f"{key}={value}")
    print(f"report_path={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

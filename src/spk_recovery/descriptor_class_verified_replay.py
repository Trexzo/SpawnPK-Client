from __future__ import annotations

"""Recompute the descriptor-class witness from source evidence, never a hand-edited queue."""

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .descriptor_class_dependencies import build_descriptor_class_dependency_report
from .descriptor_class_index_witness import build_descriptor_class_index_witness


class DescriptorClassVerifiedReplayError(ValueError):
    pass


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()


def build_descriptor_class_verified_replay(
    global_field_report: dict[str, Any],
    class_lineage: dict[str, Any],
    old_index: dict[str, Any],
    new_index: dict[str, Any],
) -> dict[str, Any]:
    """Return research-only proof derived exclusively from the global field report.

    The dependency inventory is NEVER accepted as a caller-supplied authority.
    It is reconstructed every run from the original fail-closed global evidence.
    """
    if not isinstance(global_field_report, dict):
        raise DescriptorClassVerifiedReplayError("global field report must be an object")
    if not isinstance(old_index, dict) or not isinstance(new_index, dict):
        raise DescriptorClassVerifiedReplayError("class indexes must be objects")
    if (
        global_field_report.get("old_build_id") != "v308"
        or global_field_report.get("new_build_id") != "v309"
    ):
        raise DescriptorClassVerifiedReplayError("requires exact v308->v309 global report")
    for label, index in (("old", old_index), ("new", new_index)):
        source_sha = global_field_report.get(label + "_sha256")
        index_sha = index.get("sha256")
        if (
            not isinstance(source_sha, str)
            or not isinstance(index_sha, str)
            or len(source_sha) != 64
            or source_sha.lower() != index_sha.lower()
        ):
            raise DescriptorClassVerifiedReplayError(
                f"{label} global-report SHA256 does not match exact class index"
            )

    dependencies = build_descriptor_class_dependency_report(global_field_report)
    witness = build_descriptor_class_index_witness(
        dependencies, class_lineage, old_index, new_index
    )
    if witness["dependency_report_digest"] != _digest(dependencies):
        raise DescriptorClassVerifiedReplayError("dependency derivation digest drift")

    summary = witness["summary"]
    if (
        summary["candidate_classes"] + summary["rejected_classes"]
        != summary["input_class_dependencies"]
        or summary["candidate_fields_blocked"] + summary["still_blocked_fields"]
        != dependencies["summary"]["blocked_fields"]
    ):
        raise DescriptorClassVerifiedReplayError("witness accounting drift")
    body = {
        "schema_version": 1,
        "kind": "v309_descriptor_class_verified_replay_research",
        "canonical": False,
        "state": "NO_CLASS_OR_MEMBER_IDENTITY_ACCEPTED",
        "global_field_report_id": global_field_report.get("report_id"),
        "global_field_report_digest": _digest(global_field_report),
        "class_lineage_digest": _digest(class_lineage),
        "old_index_sha256": old_index["sha256"],
        "new_index_sha256": new_index["sha256"],
        "dependency_report_digest": _digest(dependencies),
        "summary": summary,
        "candidates": witness["candidates"],
        "rejected": witness["rejected"],
        "note": (
            "Original global field evidence is the sole input to the dependency "
            "queue. Exact-index class witnesses are independently recomputed. "
            "Raw descriptor/name equality is not proof. All candidates remain "
            "research-only until a separately reviewed canonical acceptance."
        ),
    }
    return {
        "report_id": "DESCCLASSREPLAY_" + _digest(body)[:20].upper(),
        **body,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="spk-v309-descriptor-class-verified-replay")
    for name in ("global_field_report", "class_lineage", "old_index", "new_index"):
        parser.add_argument(name, type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        inputs = [
            json.loads(getattr(args, name).read_text(encoding="utf-8"))
            for name in ("global_field_report", "class_lineage", "old_index", "new_index")
        ]
        output = build_descriptor_class_verified_replay(*inputs)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(output, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"SPK_DESCRIPTOR_CLASS_VERIFIED_REPLAY_FAIL: {exc}")
        return 1
    print("SPK_DESCRIPTOR_CLASS_VERIFIED_REPLAY_PASS")
    print(f"report_id={output['report_id']}")
    for key, value in output["summary"].items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

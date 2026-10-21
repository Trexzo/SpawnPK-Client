"""Bounded original-v311 scene bytecode triage; no original source is exported.

Checks the exact owner-private JAR and scene class SHA, invokes JDK javap with
an argument vector (never a shell), and records only method descriptors and
opcode aggregate fingerprints. A role or bytecode footprint is NOT proof of
historical class/member identity or that scene bounds are correct.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import re
import subprocess
import zipfile
from typing import Any


EXPECTED_CLASS = "rs/V.class"
DECL = re.compile(r"^  (?:public|private|protected|static)\b.*[;{}]$")
OP = re.compile(r"^\s+(\d+):\s+([a-z][a-z0-9_]*)\b(.*)$")
EXPECTED_HEADER = "public final class rs.V {"


class MemberFrontierError(ValueError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def parse_javap_scene(
    text: str, *, original_sha: str, class_sha: str,
) -> dict[str, Any]:
    """Classify original v311 method role sites, without promoting names."""
    if EXPECTED_HEADER not in text.splitlines()[:8]:
        raise MemberFrontierError("MEMBER_FRONTIER_CLASS_HEADER_MISMATCH")
    methods: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in text.splitlines():
        if DECL.fullmatch(line) and (
            "(" in line or line.strip() == "static {};"
        ):
            current = {
                "signature": line.strip(), "descriptor": None, "ops": [],
            }
            methods.append(current)
            continue
        if current is None:
            continue
        if line.startswith("    descriptor: ") and current["descriptor"] is None:
            current["descriptor"] = line.split(": ", 1)[1]
            continue
        match = OP.fullmatch(line)
        if match:
            current["ops"].append(
                (int(match[1]), match[2], match[3])
            )

    if len(methods) != 66 or sum(
        method["signature"] == "static {};" for method in methods
    ) != 1:
        raise MemberFrontierError("MEMBER_FRONTIER_EXPECTED_66_METHODS")
    rows: list[dict[str, Any]] = []
    for method in methods:
        if not method["ops"]:
            raise MemberFrontierError("MEMBER_FRONTIER_EMPTY_CODE")
        descriptor = method["descriptor"] or "<clinit>"
        refs = [
            i for i, (_, op, operands) in enumerate(method["ops"])
            if op in ("getfield", "putfield")
            and re.search(
                r"Field (?:rs/V\.)?i:\[\[\[Lrs/H;", operands,
            )
        ]
        if not refs:
            continue
        # Array stores can target other arrays in the same method. This is a
        # worklist, not an alias analysis or proof of an unsafe scene write.
        counts = {
            "grid_reference_instructions": len(refs),
            "aaload_instructions": sum(
                op == "aaload" for _, op, _ in method["ops"]
            ),
            "aastore_instructions": sum(
                op == "aastore" for _, op, _ in method["ops"]
            ),
            "tile_field_puts": sum(
                op == "putfield" and "Field rs/H." in operands
                for _, op, operands in method["ops"]
            ),
            "conditional_branches_before_first_grid_field": sum(
                op.startswith("if") for _, op, _ in method["ops"][:refs[0]]
            ),
        }
        rows.append({
            "method_signature": method["signature"],
            "descriptor": descriptor,
            "signature_descriptor_sha256": hashlib.sha256(
                (method["signature"] + "\0" + descriptor).encode("utf-8")
            ).hexdigest(),
            "opcode_sequence_sha256": hashlib.sha256(
                " ".join(op for _, op, _ in method["ops"]).encode("ascii")
            ).hexdigest(),
            "instruction_lines": len(method["ops"]),
            **counts,
            "possible_mutation_review": bool(
                counts["aastore_instructions"] or counts["tile_field_puts"]
            ),
            "boundary_safety_assessed": False,
            "cross_build_method_identity_proven": False,
        })
    if len(rows) != 42:
        raise MemberFrontierError("MEMBER_FRONTIER_EXPECTED_42_GRID_METHODS")
    if sum(x["possible_mutation_review"] for x in rows) != 22:
        raise MemberFrontierError(
            "MEMBER_FRONTIER_EXPECTED_22_MUTATION_REVIEW_CANDIDATES"
        )
    return {
        "schema_version": 1,
        "kind": "v311_original_scene_method_frontier",
        "original_jar_sha256": original_sha,
        "scene_class_path": EXPECTED_CLASS,
        "scene_class_sha256": class_sha,
        "observed_class_methods": len(methods),
        "grid_referencing_methods": len(rows),
        "mutation_review_candidates": sum(
            x["possible_mutation_review"] for x in rows
        ),
        "methods": rows,
        "source_compiled": False,
        "gameplay_executed": False,
        "cross_build_member_identity_proven": False,
        "bounds_guard_correctness_proven": False,
    }


def analyze_original_scene(
    jar: Path, authority: dict[str, Any], *, javap: str = "javap",
) -> dict[str, Any]:
    if authority.get("build") != 311 or not isinstance(
        authority.get("sha256"), str
    ):
        raise MemberFrontierError("MEMBER_FRONTIER_INVALID_AUTHORITY")
    try:
        actual_sha = sha256_file(jar)
    except OSError as exc:
        raise MemberFrontierError("MEMBER_FRONTIER_JAR_UNREADABLE") from exc
    if actual_sha != authority["sha256"]:
        raise MemberFrontierError("MEMBER_FRONTIER_WRONG_ORIGINAL_JAR")
    candidate = authority.get("scene_role_candidate")
    if not isinstance(candidate, dict) or candidate.get(
        "scene_class_path"
    ) != EXPECTED_CLASS:
        raise MemberFrontierError("MEMBER_FRONTIER_SCENE_ROLE_NOT_PINNED")
    try:
        with zipfile.ZipFile(jar) as source:
            original = source.read(EXPECTED_CLASS)
    except (OSError, KeyError, zipfile.BadZipFile) as exc:
        raise MemberFrontierError(
            "MEMBER_FRONTIER_CLASS_READ_FAILED"
        ) from exc
    class_sha = hashlib.sha256(original).hexdigest()
    if class_sha != candidate.get("scene_class_sha256"):
        raise MemberFrontierError(
            "MEMBER_FRONTIER_SCENE_CLASS_HASH_MISMATCH"
        )
    try:
        completed = subprocess.run(
            [javap, "-classpath", str(jar), "-c", "-p", "-s", "rs.V"],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=45, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise MemberFrontierError(
            "MEMBER_FRONTIER_JAVAP_UNAVAILABLE_OR_TIMEOUT"
        ) from exc
    if completed.returncode or len(completed.stdout) > 4_000_000:
        raise MemberFrontierError(
            "MEMBER_FRONTIER_JAVAP_FAILED_OR_EXCESSIVE_OUTPUT"
        )
    return parse_javap_scene(
        completed.stdout,
        original_sha=authority["sha256"],
        class_sha=class_sha,
    )

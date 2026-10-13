"""R119: one SHA-pinned private original-v309 R116 -> R117 -> R118 replay.

This is an orchestration gate, NOT Java source reconstruction or runtime proof.
The original JAR is read-only and NEVER executed. Do not publish private input,
intermediate classfiles, or recovered proprietary source in GitHub.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import tempfile

from .private_original_fourth_enum_accessors import digest
from .private_v309_saver_one_fullframe_rebind_r116 import (
    normalize_saver_then_require_original_r113,
)
from .private_v309_loader_symbolic_frames_r117 import (
    normalize_original_161_frames_then_require_large_R81,
)
from .private_one_final_original_owner_r118 import (
    accept_one_final_v309_source_compiled_owner,
)

CANONICAL_V309_SHA256 = (
    "ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38"
)


class PrivateThreeStageReplayR119Error(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise PrivateThreeStageReplayR119Error(reason)


def sha_matches(path, sha):
    return (path.is_file() and not path.is_symlink()
            and isinstance(sha, str)
            and re.fullmatch(r"[a-fA-F0-9]{64}", sha) is not None
            and digest(path) == sha.lower())


def replay_source_owner(original_jar, source_compiled_jar, owner_entry,
                        surrogate_simple, output, *,
                        original_sha256, source_sha256):
    original = Path(original_jar)
    compiled = Path(source_compiled_jar)
    output = Path(output)
    require(type(original_sha256) is str
            and original_sha256.lower() == CANONICAL_V309_SHA256
            and sha_matches(original, CANONICAL_V309_SHA256),
            "PINNED_COMPLETE_ORIGINAL_V309_JAR_REQUIRED")
    require(sha_matches(compiled, source_sha256)
            and compiled.resolve() != original.resolve(),
            "SOURCE_COMPILED_JAVA9_CANDIDATE_SHA256_REQUIRED")
    require(not output.exists() and not output.is_symlink()
            and output.parent.is_dir() and not output.parent.is_symlink(),
            "FRESH_PRIVATE_OUTPUT_DIRECTORY_REQUIRED")
    require(type(owner_entry) is str and owner_entry.endswith(".class")
            and not owner_entry.startswith("/") and "\\" not in owner_entry
            and all(x not in ("", ".", "..") for x in owner_entry.split("/"))
            and type(surrogate_simple) is str
            and re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*",
                             surrogate_simple) is not None,
            "UNSAFE_OWNER_OR_SOURCE_ENUM_IDENTITY")

    with tempfile.TemporaryDirectory(prefix="v309-r119-private-",
                                     dir=output.parent) as tmp:
        root = Path(tmp)
        r116dir = root / "r116"
        saver = normalize_saver_then_require_original_r113(
            original, compiled, owner_entry, r116dir,
            original_sha256=CANONICAL_V309_SHA256,
            candidate_sha256=source_sha256,
        )
        saver_jar = r116dir / "candidate.saver-frame.PRIVATE.jar"
        saver_sha = saver.get("saver_frame_normalized_candidate_sha256")
        require(sha_matches(saver_jar, saver_sha)
                and saver.get("original_saver_R66_R81_operands_and_handlers_passed") is True
                and saver.get("original_saver_StackMapTable_frames_exact") == 10
                and saver.get("candidate_saver_Code_bytes_preserved") is True
                and saver.get("saver_original_executable_Code_transferred") is False,
                "R116_SAVER_POSTIMAGE_UNVERIFIED")

        r117dir = root / "r117"
        loader = normalize_original_161_frames_then_require_large_R81(
            original, saver_jar, owner_entry, r117dir,
            original_sha256=CANONICAL_V309_SHA256,
            candidate_sha256=saver_sha,
        )
        loader_jar = r117dir / "candidate.large-method-frames.PRIVATE.jar"
        loader_sha = loader.get("final_both_large_method_candidate_sha256")
        require(sha_matches(loader_jar, loader_sha)
                and loader.get(
                    "original_loader_161_frame_ordinals_and_verification_states_equal") is True
                and loader.get("candidate_697_executable_Code_bytes_preserved") is True
                and loader.get(
                    "original_saver_364_R113_all_operands_10_frames_exact") is True
                and loader.get("original_executable_Code_bytes_transferred") is False,
                "R117_LOADER_POSTIMAGE_UNVERIFIED")

        r118dir = root / "r118"
        owner = accept_one_final_v309_source_compiled_owner(
            original, loader_jar, owner_entry, surrogate_simple, r118dir,
            original_sha256=CANONICAL_V309_SHA256,
            candidate_sha256=loader_sha,
        )
        final_jar = r118dir / "candidate.private.jar"
        final_sha = owner.get("final_all_original_gates_candidate_sha256")
        require(sha_matches(final_jar, final_sha)
                and all(owner.get(key) is True for key in (
                    "R95_original_four_enums_passed",
                    "R94_original_nine_ordinary_owner_methods_passed",
                    "R58_original_clinit_operand_semantics_passed",
                    "R88_original_owner_all_declarations_passed",
                ))
                and owner.get("original_loader_161_verification_states_equal") is True
                and owner.get("original_saver_ten_stackmap_frames_exact") is True
                and owner.get("whole_original_client_runtime_equivalence_certified") is False,
                "R118_FINAL_OWNER_OR_ENUM_PARITY_UNVERIFIED")
        require(len({source_sha256.lower(), saver_sha, loader_sha, final_sha}) == 4,
                "PRIVATE_R116_R117_R118_POSTIMAGE_DIGESTS_NOT_DISTINCT")
        require(sha_matches(original, CANONICAL_V309_SHA256)
                and sha_matches(compiled, source_sha256)
                and sha_matches(saver_jar, saver_sha)
                and sha_matches(loader_jar, loader_sha),
                "PRIVATE_ORIGINAL_OR_SOURCE_HASH_CHANGED_DURING_REPLAY")
        report = {
            "schema_version": 1,
            "kind": "private_v309_one_source_compiled_original_replay_r119",
            "original_sha256": CANONICAL_V309_SHA256,
            "source_compiled_sha256": source_sha256.lower(),
            "r116_saver_repaired_sha256": saver_sha,
            "r117_loader_repaired_sha256": loader_sha,
            "r118_final_owner_sha256": final_sha,
            "R116_R113_original_saver_364_and_ten_frames_passed": True,
            "R117_R81_original_loader_697_and_161_states_passed": True,
            "R118_R95_R94_R58_R88_original_final_owner_passed": True,
            "original_executable_Code_bytes_copied": False,
            "whole_client_runtime_or_gameplay_equivalence_certified": False,
        }
        stage = root / "accepted"
        stage.mkdir()
        shutil.copyfile(final_jar, stage / "candidate.private.jar")
        (stage / "original-v309-r119.aggregate.json").write_text(
            json.dumps(report, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )
        require(not output.exists() and not output.is_symlink(),
                "PRIVATE_OUTPUT_OCCUPIED_DURING_REPLAY")
        os.rename(stage, output)
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    for field in ("original_jar", "source_compiled_jar", "owner_entry",
                  "surrogate_simple", "new_private_output"):
        p.add_argument(field)
    p.add_argument("--original-sha256", required=True)
    p.add_argument("--candidate-sha256", required=True)
    args = p.parse_args(argv)
    try:
        report = replay_source_owner(
            args.original_jar, args.source_compiled_jar, args.owner_entry,
            args.surrogate_simple, args.new_private_output,
            original_sha256=args.original_sha256,
            source_sha256=args.candidate_sha256)
        print(json.dumps(report, sort_keys=True))
    except Exception:
        p.error("PRIVATE_ORIGINAL_V309_R119_COMPLETE_SOURCE_REPLAY_NOT_ACCEPTED")


if __name__ == "__main__":
    main()

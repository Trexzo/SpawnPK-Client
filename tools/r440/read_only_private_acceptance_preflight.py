#!/usr/bin/env python3
"""R440 owner-only READ-ONLY admission audit for the real R421 Store baseline.

This does not patch, compile, execute game code, create a TEMP candidate,
read player history, or generate a success file. It refuses unapproved
dependency hashes and compares *user-supplied reference* hashes (whose trusted origin must
be reviewed independently); it requires exact R421 source/class
and safe R424 public patch shape before R425/R432 can be attempted.

Use with Python -B. No private source content, full inventory or local
paths are printed. Hosted tests use independently invented files only.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.r424 import prepare_private_legacy_cleanup_patch as r424
from tools.r425 import compile_and_accept_private_overlay as r425
from tools.r432 import chain_private_process_acceptance as r432
from tools.r441.approved_full_inventory import require_approved_baselines


class Refused(RuntimeError):
    pass


def require(condition: bool, code: str) -> None:
    if not condition:
        raise Refused(code)


def exact_owner_isolated_roots(source: Path, classes: Path) -> None:
    """No arbitrary source tree, installed client or relocated test workspace."""
    temp = Path(tempfile.gettempdir()).absolute()
    parent = (temp / "SpawnPK-R386-Isolated-Acceptance"
              / "R421-Private-NoFollow-Cache-Directory-Preflight")
    expected_source = parent / "Source-Candidate-R421" / "source"
    expected_classes = parent / "R421-Compiled-Classes"
    require(source.absolute() == expected_source and
            classes.absolute() == expected_classes,
            "R440_REFUSE_OUTSIDE_EXACT_R421_TEMP_WORKSPACE")
    for path in (source, classes):
        # Walk lexical parents rather than following an untrusted alias first.
        for ancestor in (path.absolute(), *path.absolute().parents):
            try:
                info = ancestor.lstat()
            except OSError:
                raise Refused("R440_MISSING_OR_UNREADABLE_PRIVATE_ANCESTOR") from None
            require(stat.S_ISDIR(info.st_mode) and not path_is_link(ancestor),
                    "R440_REFUSE_SYMLINK_OR_NON_DIRECTORY_ANCESTOR")


def path_is_link(path: Path) -> bool:
    # Python 3.12 also exposes Windows junction detection. Neither may
    # alias an installed or unrelated source tree into this acceptance.
    return path.is_symlink() or bool(
        getattr(path, "is_junction", lambda: False)())


def require_regular_tree(root: Path) -> None:
    """Reject symlinks, junctions and non-regular members before the build."""
    require(root.is_dir() and not path_is_link(root),
            "R440_INVALID_PRIVATE_TREE_ROOT")
    for member in root.rglob("*"):
        require(not path_is_link(member), "R440_REFUSE_PRIVATE_TREE_LINK")
        try:
            mode = member.lstat().st_mode
        except OSError:
            raise Refused("R440_UNREADABLE_PRIVATE_TREE_MEMBER") from None
        require(stat.S_ISDIR(mode) or stat.S_ISREG(mode),
                "R440_REFUSE_SPECIAL_PRIVATE_TREE_MEMBER")


def require_java21(java: Path, javac: Path) -> None:
    """Inspect tool versions only: no compilation, execution or game launch."""
    for path, executable in ((javac, "javac"), (java, "java")):
        require(path.is_file() and not path_is_link(path),
                "R440_JDK_EXECUTABLE_MISSING_OR_LINK")
        result = subprocess.run(
            [str(path), "-version"], capture_output=True, text=True,
            check=False, timeout=15)
        output = (result.stdout + "\n" + result.stderr)
        require(result.returncode == 0, "R440_JDK_VERSION_COMMAND_FAILED")
        if executable == "javac":
            valid = re.search(r"\bjavac\s+21(?:\.\d+){0,3}(?:\s|$)", output)
        else:
            valid = (re.search(r'\bversion\s+"21(?:[."]|$)', output)
                     or re.search(r"\bopenjdk\s+21(?:[.\s]|$)", output))
        require(valid is not None, "R440_JDK21_REQUIRED")


def validate_approved_digests(args) -> None:
    for label in ("dependency_a_sha256", "dependency_b_sha256"):
        value = getattr(args, label, None)
        require(type(value) is str and
                re.fullmatch(r"[0-9a-f]{64}", value) is not None,
                "R440_APPROVED_DEPENDENCY_SHA_REQUIRED")
    # Matching the two files to *their own freshly calculated hashes*
    # cannot establish an independently approved byte identity.
    require(args.dependency_a_sha256 != args.dependency_b_sha256,
            "R440_IDENTICAL_DEPENDENCY_DIGESTS_REVIEW_REQUIRED")


def audit(args) -> dict:
    """Pure admission/read of known private build inputs; no output files."""
    validate_approved_digests(args)
    exact_owner_isolated_roots(args.prior_source_root,
                               args.prior_classes_root)
    require_regular_tree(args.prior_source_root)
    require_regular_tree(args.prior_classes_root)
    # R425 independently validates SHA-pinned source/class, full 1,277/1,394
    # counts, provided dependency SHA matches, and accepted private paths.
    r425.validate_inputs(args)
    require_java21(args.java, args.javac)
    for public in (args.public_helper_source, args.public_acceptance_source,
                   r432.R422_HARNESS, r432.R422_PROGRAM):
        require(r432.regular_nofollow(public),
                "R440_PUBLIC_HARNESS_SOURCE_MISSING_OR_LINK")
    public_helper = args.public_helper_source.read_bytes()
    r424.canonical_helper_bytes(public_helper)

    baseline_source = r425.sha_inventory(args.prior_source_root, ".java")
    baseline_classes = r425.sha_inventory(args.prior_classes_root, ".class")
    require_approved_baselines(args, baseline_source, baseline_classes)
    dependencies_before = (
        r425.hash_file(args.dependency_a), r425.hash_file(args.dependency_b))
    # Stronger than checking only the number of files: prove the known
    # private R421 method shape is patchable with R424, in memory ONLY.
    original = (args.prior_source_root / r425.STORE).read_bytes()
    require(r425.hash_file(args.prior_source_root / r425.STORE) ==
            r424.PINNED_R421_STORE_SHA,
            "R440_PRIVATE_SOURCE_PIN_DRIFT")
    patched = r424.patch_source_text(
        original.decode("utf-8"), r424.PINNED_R421_STORE_SHA)
    require('false); // R424: hard-coded non-destructive policy' in patched,
            "R440_R424_NOT_HARDCODED_DRY_RUN")
    require("private static boolean deleteTree" not in patched,
            "R440_R424_UNSAFE_RECURSIVE_DELETION_PRESENT")

    require(baseline_source == r425.sha_inventory(args.prior_source_root, ".java")
            and baseline_classes ==
                r425.sha_inventory(args.prior_classes_root, ".class")
            and dependencies_before ==
                (r425.hash_file(args.dependency_a),
                 r425.hash_file(args.dependency_b)),
            "R440_OWNER_INPUT_CHANGED_DURING_AUDIT")
    return {
        "status": "R440_OWNER_PRIVATE_READ_ONLY_PREFLIGHT_PASS",
        "source_count": len(baseline_source),
        "class_count": len(baseline_classes),
        "r421_source_sha256_verified": True,
        "r421_class_sha256_verified": True,
        "provided_reference_dependency_digests_matched": True,
        "provided_reference_full_source_class_inventories_matched": True,
        "public_r424_helper_verified": True,
        "r424_source_shape_checked_in_memory": True,
        "jdk21_verified": True,
        "private_source_read": True,
        "live_history_opened": False,
        "client_started": False,
        "candidate_created": False,
        "private_java_compiled": False,
        "release_authorized": False,
        "merge_authorized": False,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prior-source-root", type=Path, required=True)
    parser.add_argument("--prior-classes-root", type=Path, required=True)
    parser.add_argument("--dependency-a", type=Path, required=True)
    parser.add_argument("--dependency-b", type=Path, required=True)
    parser.add_argument("--dependency-a-sha256", required=True)
    parser.add_argument("--dependency-b-sha256", required=True)
    parser.add_argument("--approved-source-inventory-sha256", required=True)
    parser.add_argument("--approved-class-inventory-sha256", required=True)
    parser.add_argument("--public-helper-source", type=Path, required=True)
    parser.add_argument("--public-acceptance-source", type=Path, required=True)
    parser.add_argument("--javac", type=Path, required=True)
    parser.add_argument("--java", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = audit(args)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (Refused, r425.Refused, r424.Refused, OSError, UnicodeError,
            subprocess.TimeoutExpired, ValueError, RuntimeError) as error:
        reason = (str(error) if isinstance(error,
                    (Refused, r425.Refused, r424.Refused))
                  else "R440_INVALID_PRIVATE_PREFLIGHT_INPUT")
        print(json.dumps({
            "status": "R440_OWNER_PRIVATE_READ_ONLY_PREFLIGHT_REFUSED",
            "reason": reason[:160],
            "release_authorized": False,
            "merge_authorized": False,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

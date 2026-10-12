"""R104: compose R98 collision fix and R103 metadata rewrite, gate with R95.

Operate only on private SHA-pinned candidate/original JARs. Compose transformations
on one private temporary candidate: collision-safe post-javac fourth-enum
binary-name rebinding (R98) and exact original ordered six-entry owner
InnerClasses restoration (R103), then require R95 to accept *all four* enum
methods and class metadata. No partial output on failure. R97 still separate.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from zipfile import ZipFile

from .private_four_nested_enum_acceptance import (
    FourNestedEnumAcceptanceError, nested_entries,
    symbolic_innerclasses_table, replay_private_four_enum_gate,
)
from .private_nested_enum_collision_rebind import (
    CollisionRebindError, rebind_classfile,
)
from .private_original_owner_innerclasses_rebuilder_r103 import (
    OriginalOwnerInnerClassesError, digest, replace_owner_innerclasses,
    _validate_table,
)


class AllFourPrivateEnumAcceptanceError(ValueError):
    pass


def need(condition, reason):
    if not condition:
        raise AllFourPrivateEnumAcceptanceError(reason)


def assemble_private_four_enum_candidate(
    original_jar, candidate_jar, owner_entry, surrogate_simple, output,
    *, original_sha256, candidate_sha256,
):
    original_jar, candidate_jar, output = map(
        Path, (original_jar, candidate_jar, output))
    need(output.parent.is_dir() and not output.parent.is_symlink()
         and not output.exists() and not output.is_symlink(),
         "NEW_PRIVATE_OUTPUT_REQUIRED")
    need(original_jar.resolve() != candidate_jar.resolve(),
         "ORIGINAL_AND_CANDIDATE_JARS_MUST_DIFFER")
    for path, pin in ((original_jar, original_sha256),
                      (candidate_jar, candidate_sha256)):
        need(path.is_file() and not path.is_symlink()
             and isinstance(pin, str)
             and re.fullmatch(r"[a-fA-F0-9]{64}", pin)
             and digest(path) == pin.lower(),
             "ORIGINAL_OR_CANDIDATE_COMPLETE_JAR_SHA256_MISMATCH")
    need(type(owner_entry) is str and owner_entry.endswith(".class")
         and not owner_entry.startswith("/")
         and "\\" not in owner_entry
         and all(s not in ("", ".", "..") for s in owner_entry.split("/"))
         and type(surrogate_simple) is str
         and re.fullmatch(r"[A-Za-z_$][A-Za-z0-9_$]*", surrogate_simple),
         "OWNER_OR_SURROGATE_JVM_ENTRY_UNSAFE")

    owner = owner_entry[:-6]
    outer_simple = owner.rsplit("/", 1)[-1]
    need(outer_simple != surrogate_simple,
         "SURROGATE_MUST_NOT_EQUAL_COLLIDING_ORIGINAL_NAME")
    original_fourth = owner + "$" + outer_simple + ".class"
    candidate_surrogate = owner + "$" + surrogate_simple + ".class"
    with ZipFile(original_jar) as old, ZipFile(candidate_jar) as new:
        old_names, new_names = old.namelist(), new.namelist()
        need(len(old_names) == len(set(old_names))
             and len(new_names) == len(set(new_names))
             and old_names.count(owner_entry) == 1
             and new_names.count(owner_entry) == 1,
             "ORIGINAL_OR_CANDIDATE_OWNER_NOT_UNIQUE")
        try:
            original_nested = nested_entries(old_names, owner_entry)
            candidate_nested = nested_entries(new_names, owner_entry)
        except FourNestedEnumAcceptanceError as exc:
            raise AllFourPrivateEnumAcceptanceError(
                "FOUR_ORIGINAL_AND_CANDIDATE_ENUM_CLASSFILES_REQUIRED"
            ) from exc
        need(original_fourth in original_nested
             and candidate_surrogate in candidate_nested
             and original_fourth not in new_names
             and set(original_nested) - {original_fourth} ==
                 set(candidate_nested) - {candidate_surrogate},
             "FOUR_NESTED_ENUM_BINARIES_NOT_ALIGNED")
        need(old.read(owner_entry)[4:8] == new.read(owner_entry)[4:8],
             "ORIGINAL_AND_CANDIDATE_JAVA_CLASS_VERSION_MISMATCH")
        try:
            original_table = symbolic_innerclasses_table(old.read(owner_entry))
            _validate_table(original_table, owner)
        except (FourNestedEnumAcceptanceError,
                OriginalOwnerInnerClassesError) as exc:
            raise AllFourPrivateEnumAcceptanceError(
                "SIX_ORIGINAL_OWNER_INNERCLASSES_ROWS_UNSUPPORTED"
            ) from exc

        with tempfile.TemporaryDirectory(
            prefix="v309-all-four-r104-", dir=output.parent,
        ) as temporary:
            staging = Path(temporary)
            candidate_rebound = staging / "four-enums-rebound.private.jar"
            rewritten_cp_entries = 0
            original_candidate_owner_bytes = new.read(owner_entry)
            with ZipFile(candidate_rebound, "w") as dest:
                for entry in new.infolist():
                    name = entry.filename
                    need(not name.startswith("/")
                         and "\\" not in name
                         and all(x not in ("", ".", "..")
                                 for x in name.split("/")),
                         "UNSAFE_PRIVATE_CANDIDATE_ARCHIVE_ENTRY")
                    data = new.read(entry)
                    if name.endswith(".class"):
                        try:
                            data, _ = rebind_classfile(data, owner, surrogate_simple)
                        except (CollisionRebindError,
                                ValueError, IndexError, KeyError) as exc:
                            raise AllFourPrivateEnumAcceptanceError(
                                "CANDIDATE_FOURTH_ENUM_REBIND_NOT_ACCEPTED"
                            ) from exc
                    if name == owner_entry:
                        try:
                            data, rewritten_cp_entries = (
                                replace_owner_innerclasses(
                                    data, owner, original_table))
                        except (OriginalOwnerInnerClassesError,
                                ValueError, IndexError, KeyError) as exc:
                            raise AllFourPrivateEnumAcceptanceError(
                                "CANDIDATE_SIX_OWNER_INNERCLASSES_REBUILD_FAILED"
                            ) from exc
                    if name == candidate_surrogate:
                        entry.filename = original_fourth
                    dest.writestr(entry, data)
            with ZipFile(candidate_rebound) as result:
                rewritten_names = result.namelist()
                need(len(rewritten_names) == len(set(rewritten_names))
                     and original_fourth in rewritten_names
                     and candidate_surrogate not in rewritten_names,
                     "REBOUND_ARCHIVE_ENUM_IDENTITY_COLLISION")
                need(symbolic_innerclasses_table(
                    result.read(owner_entry)) == original_table,
                    "REBOUND_OWNER_SIX_INNERCLASSES_NOT_EXACT")

            changed_sha = digest(candidate_rebound)
            try:
                proof = replay_private_four_enum_gate(
                    original_jar, candidate_rebound,
                    owner_entry, staging / "r95",
                    original_sha256=original_sha256,
                    candidate_sha256=changed_sha,
                )
            except (FourNestedEnumAcceptanceError,
                    ValueError, OSError) as exc:
                raise AllFourPrivateEnumAcceptanceError(
                    "R95_ALL_FOUR_ORIGINAL_ENUM_PARITY_NOT_ACCEPTED"
                ) from exc
            need(proof.get("original_nested_enum_classes_verified") == 4
                 and proof.get("symbolic_InnerClasses_tables_identical_all_four")
                 and proof.get("original_candidate_owner_InnerClasses_tables_identical"),
                 "R95_REQUIRED_FOUR_ENUM_AND_OWNER_TABLE_FLAGS_MISSING")
            need(digest(original_jar) == original_sha256.lower()
                 and digest(candidate_jar) == candidate_sha256.lower()
                 and digest(candidate_rebound) == changed_sha,
                 "PINNED_JARS_CHANGED_DURING_R95_REPLAY")
            accepted = staging / "accepted"
            accepted.mkdir()
            shutil.copyfile(
                candidate_rebound,
                accepted / "all-four-enums-r95-accepted.private.jar",
            )
            report = {
                "schema_version": 1,
                "kind": "v309_private_post_javac_all_four_enum_and_owner_metadata",
                "original_complete_jar_sha256": original_sha256.lower(),
                "original_source_candidate_sha256": candidate_sha256.lower(),
                "r95_accepted_candidate_sha256": changed_sha,
                "accepted_original_nested_enum_classes": 4,
                "exact_ordered_owner_InnerClasses_rows": 6,
                "exact_candidate_nested_enum_InnerClasses_tables": True,
                "exact_candidate_owner_InnerClasses_table": True,
                "source_candidate_existing_owner_method_code_preserved": True,
                "class_level_cp_entries_added": rewritten_cp_entries,
                "original_executable_bytecode_transferred": False,
                "R95_all_four_enums_exact_parity_passed": True,
                "R97_complete_owner_source_gate_passed": False,
                "whole_client_runtime_equivalence_certified": False,
            }
            with (accepted / "all-four-r95.aggregate.json").open(
                "x", encoding="utf-8", newline="\n",
            ) as stream:
                json.dump(report, stream, sort_keys=True, indent=2)
                stream.write("\n")
            need(not output.exists() and not output.is_symlink(),
                 "PRIVATE_OUTPUT_OCCUPIED_AFTER_VERIFICATION")
            os.rename(accepted, output)
            return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for n in ("original_jar", "candidate_jar", "owner_entry",
              "surrogate_simple", "new_private_output"):
        parser.add_argument(n)
    parser.add_argument("--original-sha256", required=True)
    parser.add_argument("--candidate-sha256", required=True)
    args = parser.parse_args(argv)
    try:
        result = assemble_private_four_enum_candidate(
            args.original_jar, args.candidate_jar, args.owner_entry,
            args.surrogate_simple, args.new_private_output,
            original_sha256=args.original_sha256,
            candidate_sha256=args.candidate_sha256,
        )
        print(json.dumps(result, sort_keys=True))
    except (AllFourPrivateEnumAcceptanceError,
            OriginalOwnerInnerClassesError,
            CollisionRebindError,
            FourNestedEnumAcceptanceError,
            ValueError, OSError, EOFError):
        parser.error("PRIVATE_R104_R95_ALL_FOUR_ENUM_ACCEPTANCE_FAILED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

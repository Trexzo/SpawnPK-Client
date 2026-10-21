"""Verify independently rebuilt original client classes without binary fallback.

Local-only source acceptance: the exact original JAR stays private, and javac
receives no original game JAR or original game class directory. This proves
public declaration + disassembled Code instruction parity (including byte
offsets, branch targets and resolved constant operands), not complete
classfile/StackMapTable identity or full client parity.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Any
import zipfile

from .classfile_utf8_remap import ClassfileRemapError, remap_classfile_utf8
from .source_dependency_closure import SourceClosureError, require_selected_source_closure
from .standalone_source_alias import (
    StandaloneAliasError, validate_compile_aliases,
    rename_owned_class_source, rewrite_reviewed_external_type_alias,
)


class StandaloneSourceParityError(ValueError):
    pass


_CLASS_RE = re.compile(r"rs/(?:[A-Za-z_$][A-Za-z_$0-9]*/)*[A-Za-z_$][A-Za-z_$0-9]*\.class\Z")
_INSTRUCTION_RE = re.compile(r"^\s*(\d+):\s+([a-z][a-z0-9_]*)(?:\s+(.+))?$")


def _digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def _require(ok: bool, reason: str) -> None:
    if not ok:
        raise StandaloneSourceParityError(reason)


def require_compilable_source_namespace(class_entries: set[str]) -> None:
    """Refuse unrenamed class/package collisions in the selected source island.

    Java cannot simultaneously compile `rs.t` and `package rs.t; class f`
    as source in one unrenamed compilation unit. Detection is limited to
    selected entries, not unrelated original classes on the private JAR.
    """
    _require(all(_CLASS_RE.fullmatch(n) is not None for n in class_entries),
             "INVALID_CLASS_PATH")
    internal = {n[:-6] for n in class_entries}
    for name in sorted(internal):
        parts = name.split("/")
        for i in range(1, len(parts)):
            parent = "/".join(parts[:i])
            _require(parent not in internal, "SOURCE_CLASS_PACKAGE_COLLISION")


def _normalize_javap(result: str) -> tuple[tuple[str, ...], int]:
    """Compare declarations, exact Code offsets/operands and exception handlers.

    Only numeric constant-pool slots are replaceable; preserve symbolic
    targets and exact exception-handler start/end/target/catch type. Do not
    pretend this verifies StackMapTable, attributes or runtime behavior.
    """
    rows: list[str] = []
    instruction_count = 0
    in_exception_table = False
    handler_rows = 0
    for raw in result.splitlines():
        line = raw.rstrip()
        if line.startswith("Compiled from "):
            continue
        stripped = line.strip()
        if stripped == "Exception table:":
            _require(not in_exception_table, "NESTED_EXCEPTION_TABLE")
            in_exception_table = True
            handler_rows = 0
            rows.append("EXCEPTION TABLE")
            continue
        if in_exception_table:
            if re.fullmatch(r"from\s+to\s+target\s+type", stripped):
                continue
            handler = re.fullmatch(
                r"\s*(\d+)\s+(\d+)\s+(\d+)\s+(Class [\w/$]+|any)\s*",
                line,
            )
            if handler:
                start, end, target, catch_type = handler.groups()
                _require(int(start) < int(end),
                         "MALFORMED_EXCEPTION_HANDLER_RANGE")
                rows.append(
                    f"HANDLER {int(start)} {int(end)} {int(target)} {catch_type}"
                )
                handler_rows += 1
                continue
            _require(handler_rows > 0, "EMPTY_EXCEPTION_TABLE")
            _require(not re.match(r"^\s+\d", line),
                     "MALFORMED_EXCEPTION_HANDLER_ROW")
            in_exception_table = False

        match = _INSTRUCTION_RE.fullmatch(line)
        if match:
            offset, opcode, operands = match.groups()
            operand = (operands or "").strip()
            if "#" in operand:
                _require("//" in operand, "UNRESOLVED_JAVAP_CONSTANT_POOL_OPERAND")
                before, comment = operand.split("//", 1)
                # #N is only a *constant-pool index*. Keep all remaining
                # operands, exact offsets, symbolic comments and branch sites.
                before = re.sub(r"#\d+\b", "#CP", before)
                operand = before.strip() + " // " + comment.strip()
            rows.append(
                str(int(offset)) + ": " + opcode + (" " + operand if operand else "")
            )
            instruction_count += 1
            continue
        if not stripped or stripped in ("Code:", "}", "{"):
            continue
        if line.startswith("  ") and not line.startswith("    "):
            rows.append("DECL " + stripped)
        elif line.startswith("    descriptor: "):
            rows.append("DESC " + stripped[len("descriptor: "):])
        elif stripped.endswith(" {") and ("class " in stripped or "interface " in stripped):
            rows.append("CLASS " + stripped)
        elif stripped.startswith("static {};"):
            rows.append("DECL " + stripped)
    _require(not in_exception_table or handler_rows > 0, "EMPTY_EXCEPTION_TABLE")
    # An original JVM interface can have abstract method declarations
    # without any Code attributes. Verify its full declarations and method
    # descriptors rather than rejecting legitimate zero-opcode interfaces.
    # A concrete class or truncated disassembly must still fail closed.
    if instruction_count == 0:
        _require(
            any(
                x.startswith("CLASS ") and re.search(
                    r"\binterface\s+[^{}]+\{$", x
                ) is not None
                for x in rows
            )
            and any(x.startswith("DECL ") for x in rows)
            and any(x.startswith("DESC ") for x in rows),
            "DISASSEMBLY_HAS_NO_INSTRUCTIONS",
        )
    _require(any(x.startswith("CLASS ") for x in rows),
             "DISASSEMBLY_MISSING_CLASS")
    _require(any(x.startswith("DECL ") for x in rows),
             "DISASSEMBLY_MISSING_DECLARATIONS")
    return tuple(rows), instruction_count


def _javap(javap: str, classpath: Path, classname: str) -> tuple[tuple[str, ...], int]:
    try:
        run = subprocess.run(
            [javap, "-classpath", str(classpath), "-c", "-p", "-s", classname],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=50, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise StandaloneSourceParityError("JAVAP_UNAVAILABLE_OR_TIMEOUT") from exc
    _require(run.returncode == 0 and len(run.stdout) < 4_000_000,
             "JAVAP_FAILURE_OR_EXCESSIVE_OUTPUT")
    return _normalize_javap(run.stdout)


def verify_standalone_sources(
    original_jar: Path, source_root: Path, output_root: Path,
    *, original_sha256: str, class_sha256: dict[str, str],
    javac: str = "javac", javap: str = "javap",
    compile_aliases: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build exact selected source classes with no game binary classpath.

    output_root must not exist; selected source files must be ordinary local
    files. A failed compile/verification leaves private intermediate files
    but does not publish an acceptance report.
    """
    _require(re.fullmatch(r"[0-9a-f]{64}", original_sha256) is not None,
             "INVALID_ORIGINAL_SHA256_PIN")
    # Bounded expansion allows the 23-class original-v311 source island,
    # without accepting an unreviewed whole-client compilation attempt.
    _require(bool(class_sha256) and len(class_sha256) <= 64, "INVALID_CLASS_SET")
    _require(not output_root.exists() and not output_root.is_symlink(),
             "OUTPUT_ALREADY_EXISTS")
    original_jar = original_jar.resolve()
    source_root = source_root.resolve()
    _require(original_jar.is_file() and source_root.is_dir(), "INPUT_MISSING")
    _require(_digest(original_jar) == original_sha256, "WRONG_ORIGINAL_JAR")
    selected: dict[str, str] = {}
    for entry, digest in sorted(class_sha256.items()):
        _require(_CLASS_RE.fullmatch(entry) is not None, "INVALID_CLASS_PATH")
        _require(re.fullmatch(r"[0-9a-f]{64}", digest) is not None,
                 "INVALID_CLASS_SHA256_PIN")
        selected[entry] = digest
    closure_report: dict[str, Any] | None = None
    try:
        with zipfile.ZipFile(original_jar) as z:
            names = [x.filename for x in z.infolist()]
            _require(len(names) == len(set(names)), "AMBIGUOUS_ORIGINAL_ZIP_ENTRIES")
            for entry, expected in selected.items():
                _require(entry in names, "MISSING_ORIGINAL_CLASS")
                blob = z.read(entry)
                _require(hashlib.sha256(blob).hexdigest() == expected,
                         "WRONG_ORIGINAL_CLASS")
                _require(blob[:8] == bytes.fromhex("cafebabe00000035"),
                         "EXPECTED_JAVA9_ORIGINAL_CLASS")
            try:
                closure_report = require_selected_source_closure(
                    z, set(selected)
                )
            except SourceClosureError as exc:
                raise StandaloneSourceParityError(str(exc)) from exc
    except (zipfile.BadZipFile, EOFError, OSError) as exc:
        raise StandaloneSourceParityError("INVALID_ORIGINAL_ARCHIVE") from exc

    # Exact reviewed compile-only alias. It is NOT semantic renaming.
    # Preserve original class names on every accepted evidence report.
    aliases = validate_compile_aliases(
        set(selected), compile_aliases or {}, set(names)
    )
    try:
        require_compilable_source_namespace(
            {aliases.get(entry, entry) for entry in selected}
        )
    except StandaloneSourceParityError as exc:
        raise StandaloneSourceParityError(
            "COMPILE_ALIAS_CLASS_PACKAGE_COLLISION_REMAINS"
        ) from exc

    originals: dict[str, Path] = {}
    source_digests: dict[str, str] = {}
    source_text: dict[str, str] = {}
    for entry in selected:
        rel = entry[:-6] + ".java"
        src = source_root / rel
        _require(not src.is_symlink() and src.is_file(),
                 "SOURCE_FILE_MISSING_OR_SYMLINK")
        _require(src.resolve().is_relative_to(source_root),
                 "SOURCE_ESCAPES_PRIVATE_ROOT")
        originals[entry] = src
        source_digests[entry] = _digest(src)
        if aliases:
            try:
                source_text[entry] = src.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError) as exc:
                raise StandaloneSourceParityError(
                    "COMPILE_ALIAS_SOURCE_UNREADABLE"
                ) from exc

    # Prepare every source transformation *before* making output folders.
    # External references are supported ONLY for same-package superclass
    # declarations, never for arbitrary Java identifiers or reflection.
    staged_text: dict[str, str] = {}
    if aliases:
        for entry, text_value in source_text.items():
            if entry in aliases:
                transformed = rename_owned_class_source(
                    text_value, old_entry=entry, alias_entry=aliases[entry]
                )
            else:
                transformed = text_value
                for renamed_entry, alias_entry in aliases.items():
                    transformed = rewrite_reviewed_external_type_alias(
                        transformed,
                        old_entry=renamed_entry,
                        alias_entry=alias_entry,
                        referring_entry=entry,
                    )
            staged_text[entry] = transformed

    # Private outputs only; the canonical Java tree is never modified.
    output_root.mkdir(parents=True, exist_ok=False)
    cls = output_root / "classes"
    cp = output_root / "empty-classpath"
    srcpath = output_root / "empty-sourcepath"
    for directory in (cls, cp, srcpath):
        directory.mkdir()
    sources: list[Path] = []
    if aliases:
        stage = output_root / "alias-sources"
        stage.mkdir()
        for entry in selected:
            changed = staged_text[entry]
            if changed != source_text[entry]:
                dest = stage / (aliases.get(entry, entry)[:-6] + ".java")
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(changed, encoding="utf-8", newline="")
                sources.append(dest)
            else:
                sources.append(originals[entry])
    else:
        sources = list(originals.values())

    cmd = [
        javac, "--release", "9", "-proc:none", "-g:none", "-encoding", "UTF-8",
        "-classpath", str(cp), "-sourcepath", str(srcpath),
        "-d", str(cls),
        *[str(p) for p in sources],
    ]
    try:
        compiler = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=120, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise StandaloneSourceParityError("JAVAC_UNAVAILABLE_OR_TIMEOUT") from exc
    _require(compiler.returncode == 0, "INDEPENDENT_SOURCE_COMPILE_FAILED")

    actual_classes = {
        p.relative_to(cls).as_posix()
        for p in cls.rglob("*.class") if p.is_file()
    }
    _require(
        actual_classes == {aliases.get(entry, entry) for entry in selected},
        "COMPILED_CLASS_SET_MISMATCH",
    )

    # Restore exact ORIGINAL identities in copied classfile metadata, before
    # comparing javap. A textual javap substitution could conceal changed
    # symbolic targets or reflection literals, so use the existing bounded
    # JVM constant-pool remapper (which refuses touching CONSTANT_String).
    comparison_dir = cls
    if aliases:
        comparison_dir = output_root / "restored-classfiles"
        comparison_dir.mkdir()
        reverse = {
            new[:-6]: old[:-6] for old, new in aliases.items()
        }
        for entry in selected:
            actual = cls / aliases.get(entry, entry)
            try:
                restored = remap_classfile_utf8(
                    actual.read_bytes(), reverse
                )
            except ClassfileRemapError as exc:
                raise StandaloneSourceParityError(
                    "COMPILE_ALIAS_INVERSE_CLASSFILE_REFUSED"
                ) from exc
            if entry in aliases:
                _require(restored.replacement_count > 0,
                         "COMPILE_ALIAS_INVERSE_CLASSFILE_NOT_APPLIED")
            dest = comparison_dir / entry
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(restored.data)

    witnesses: list[dict[str, Any]] = []
    for entry, expected_sha in selected.items():
        compiled = cls / aliases.get(entry, entry)
        blob = compiled.read_bytes()
        _require(blob[:8] == bytes.fromhex("cafebabe00000035"),
                 "COMPILED_CLASS_NOT_JAVA9")
        classname = entry[:-6].replace("/", ".")
        original_rows, original_insns = _javap(javap, original_jar, classname)
        recovered_rows, recovered_insns = _javap(javap, comparison_dir, classname)
        _require(original_rows == recovered_rows,
                 "ORDERED_JVM_INSTRUCTIONS_OR_DECLARATIONS_MISMATCH " + entry)
        _require(original_insns == recovered_insns,
                 "JVM_INSTRUCTION_COUNT_MISMATCH")
        witness = {
            "class_entry": entry,
            "original_class_sha256": expected_sha,
            "rebuilt_class_sha256": hashlib.sha256(blob).hexdigest(),
            "candidate_source_sha256": source_digests[entry],
            "ordered_instruction_count": original_insns,
            "declaration_and_instruction_sha256": hashlib.sha256(
                json.dumps(original_rows, ensure_ascii=False, separators=(",", ":"))
                .encode("utf-8")
            ).hexdigest(),
            "ordered_symbolic_instruction_parity": True,
            "matched_exception_handler_entries": sum(
                line.startswith("HANDLER ") for line in original_rows
            ),
            "java_release": 9,
            "compile_only_class_alias": aliases.get(entry),
            "original_game_binary_on_compile_classpath": False,
            "full_classfile_attribute_or_runtime_parity": "NOT_PROVEN",
        }
        witnesses.append(witness)
    report = {
        "schema_version": 1,
        "kind": "v311_independent_source_rebuild_parity",
        "original_jar_sha256": original_sha256,
        "total_classes": len(witnesses),
        "total_ordered_instructions": sum(
            x["ordered_instruction_count"] for x in witnesses
        ),
        "results": witnesses,
        "all_passed": True,
        "compile_only_class_alias_count": len(aliases),
        "canonical_source_modified": False,
        "complete_v311_source_recovery": False,
        "original_game_binary_on_compile_classpath": False,
        "explicit_original_project_dependency_closure": closure_report,
        "full_classfile_or_graphical_parity": "NOT_PROVEN",
    }
    # Detect concurrent or accidental changes to canonical source during
    # construction/compilation before issuing evidence.
    for entry, source in originals.items():
        _require(_digest(source) == source_digests[entry],
                 "CANONICAL_SOURCE_MODIFIED_DURING_COMPILE")
    result_path = output_root / "SOURCE-REBUILD-VERIFY.json"
    result_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report

#!/usr/bin/env python3
"""R393 read-only private-kit plugin-startup risk inventory.

Looks at Java source text only; executes no client, initializes no class,
and writes no private source. Reports counts/indicator names, never code bodies.
Nested/callback paths may be counted although not executed at startup.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat
import zipfile

PIN = re.compile(r"[0-9a-f]{64}\Z")
MAX_KIT = 64 * 1024 * 1024
MAX_SOURCE = 5 * 1024 * 1024
MAX_TOTAL = 150 * 1024 * 1024
REQUIRED = ("source/rs/pkg42/Class255.java",
            "source/rs/plugins/PluginManager.java")
SOURCE_PREFIX = "source/"
PLUGIN_PREFIX = "source/rs/plugins/"
START = re.compile(r"\b(?:public|protected|private)\s+(?:final\s+)?void\s+startUp\s*\(\s*\)\s*(?:throws\s+[\w\s,.]+)?\s*\{")
EXTENDS = re.compile(r"\bextends\s+Plugin\b")
CONSTRUCT = re.compile(r"\bnew\s+(?:[\w$]+\.)*([A-Z]\w*)\s*(?:<[^;{}()]*>)?\s*\(")

# Textual evidence within startUp() or explicitly named one-hop constructors.
# No inference of dynamic dispatch, actual startup enablement or reachability.
FLAGS = {
    "cleanup": r"\b(?:deleteStale|deleteTree|deleteIfExists)\s*\(|\bFiles\s*\.\s*delete\s*\(|\.delete\s*\(",
    "write": r"\b(?:seedDefaultsIfEmpty|saveFolder|writeFolderOrderSettings)\s*\(|\bFiles\s*\.\s*(?:write|move|copy|newOutputStream)\s*\(|new\s+(?:FileWriter|FileOutputStream)\s*\(",
    "read": r"\b(?:loadFolder|readAll|readAllBytes|newInputStream)\s*\(|\bstore\s*\.\s*load\s*\(|new\s+(?:FileReader|FileInputStream)\s*\(",
    "wait": r"\b(?:Thread\s*\.\s*sleep|SwingUtilities\s*\.\s*invokeAndWait)\s*\(|\.(?:join|awaitTermination)\s*\(",
    "network": r"\bnew\s+(?:Socket|DatagramSocket|URL|HttpClient)\s*\(|\.(?:openConnection|openStream|connect)\s*\(",
    "process": r"\bnew\s+ProcessBuilder\s*\(|\bRuntime\s*\.\s*getRuntime\s*\(\s*\)\s*\.\s*exec\s*\(",
    "thread": r"\bnew\s+Thread\s*\(|\bExecutors\s*\.\s*new\w*Thread\w*\s*\(",
    "ui": r"\b(?:addNavigation|createNavigationButton|setVisible)\s*\(|\bnew\s+\w*Panel\s*\(",
}
RULES = {name: re.compile(pattern) for name, pattern in FLAGS.items()}
CONSTRUCTOR_RE_CACHE: dict[str, re.Pattern] = {}


class Refused(ValueError):
    pass


def mask_java(source: str) -> str:
    """Preserve Java code positions/braces while ignoring comments and literals."""
    output = [" "] * len(source)
    state = "code"
    i = 0
    n = len(source)
    while i < n:
        ch = source[i]
        nxt = source[i:i+3]
        pair = source[i:i+2]
        if ch in "\r\n":
            output[i] = ch
        if state == "code":
            if pair == "//":
                state = "line"; i += 2; continue
            if pair == "/*":
                state = "block"; i += 2; continue
            if nxt == '"""':
                state = "textblock"; i += 3; continue
            if ch == '"':
                state = "string"; i += 1; continue
            if ch == "'":
                state = "char"; i += 1; continue
            output[i] = ch
        elif state == "line":
            if ch == "\n":
                state = "code"
        elif state == "block":
            if pair == "*/":
                state = "code"; i += 2; continue
        elif state in ("string", "char"):
            if ch == "\\":
                i += 2; continue
            if (state == "string" and ch == '"') or (state == "char" and ch == "'"):
                state = "code"
        elif state == "textblock":
            if nxt == '"""':
                state = "code"; i += 3; continue
        i += 1
    return "".join(output)


def braced_body(masked: str, opening: int) -> str:
    if opening < 0 or opening >= len(masked) or masked[opening] != "{":
        raise Refused("BAD_METHOD_BRACE")
    depth = 1
    i = opening + 1
    while i < len(masked):
        if masked[i] == "{":
            depth += 1
        elif masked[i] == "}":
            depth -= 1
            if depth == 0:
                return masked[opening+1:i]
        i += 1
    raise Refused("UNBALANCED_METHOD_BRACES")


def method_bodies(masked: str, definition: re.Pattern) -> list[str]:
    result = []
    for match in definition.finditer(masked):
        opening = masked.find("{", match.start(), match.end())
        result.append(braced_body(masked, opening))
    return result


def constructor_pattern(name: str) -> re.Pattern:
    if name not in CONSTRUCTOR_RE_CACHE:
        # Java permits constructors directly after an opening class brace on
        # the same line; don't assume a declaration begins at column zero.
        # Require a declaration boundary, not a 'new ClassName(...)' call.
        CONSTRUCTOR_RE_CACHE[name] = re.compile(
            r"(?m)(?:^[ \t]*|(?<=[;{}])[ \t]*)"
            r"(?:(?:public|private|protected)\s+)?"
            + re.escape(name) + r"\s*\([^;{}]*\)\s*(?:throws\s+[\w\s,.]+)?\s*\{"
        )
    return CONSTRUCTOR_RE_CACHE[name]


def indicators(body: str) -> list[str]:
    return sorted(k for k, pattern in RULES.items() if pattern.search(body))


def archive_safe(info: zipfile.ZipInfo) -> bool:
    raw = info.filename
    name = raw[:-1] if info.is_dir() and raw.endswith("/") else raw
    if (not name or info.orig_filename != raw or "\\" in raw
            or raw.startswith("/") or ":" in raw or "//" in raw):
        return False
    parts = PurePosixPath(name).parts
    if any(p in ("", ".", "..") for p in name.split("/")):
        return False
    if info.create_system == 3 and stat.S_IFMT(info.external_attr >> 16) == stat.S_IFLNK:
        return False
    return all(part not in ("", ".", "..") for part in parts)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pinned_archive(path: Path, sha: str) -> None:
    if not PIN.fullmatch(sha):
        raise Refused("INVALID_SHA256_PIN")
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_KIT:
        raise Refused("UNSAFE_KIT")
    if sha256_file(path) != sha:
        raise Refused("KIT_SHA256_DRIFT")


def load_sources(kit: Path, expected_sources: int) -> dict[str, str]:
    if expected_sources < 6 or expected_sources > 5000:
        raise Refused("INVALID_SOURCE_COUNT")
    sources = {}
    seen = set()
    total = 0
    try:
        with zipfile.ZipFile(kit) as archive:
            for info in archive.infolist():
                if not archive_safe(info):
                    raise Refused("UNSAFE_ZIP_ENTRY")
                if info.filename in seen:
                    raise Refused("DUPLICATE_ZIP_ENTRY")
                seen.add(info.filename)
                if info.is_dir() or not info.filename.startswith(SOURCE_PREFIX) or not info.filename.endswith(".java"):
                    continue
                if info.file_size < 1 or info.file_size > MAX_SOURCE:
                    raise Refused("SOURCE_SIZE_LIMIT")
                total += info.file_size
                if total > MAX_TOTAL:
                    raise Refused("TOTAL_SIZE_LIMIT")
                data = archive.read(info)
                if len(data) != info.file_size:
                    raise Refused("SIZE_DRIFT")
                sources[info.filename] = mask_java(data.decode("utf-8"))
    except (zipfile.BadZipFile, UnicodeDecodeError, OSError, RuntimeError) as err:
        raise Refused("KIT_READ_FAILED") from err
    if len(sources) != expected_sources:
        raise Refused("SOURCE_COUNT_DRIFT")
    if any(p not in sources for p in REQUIRED):
        raise Refused("STARTUP_ANCHORS_MISSING")
    return sources


def audit_sources(sources: dict[str, str]) -> dict:
    bootstrap = sources.get(REQUIRED[0], "")
    manager = sources.get(REQUIRED[1], "")
    if not (re.search(r"\bloadPlugins\s*\(", bootstrap)
            and re.search(r"\bstartPlugins\s*\(", bootstrap)
            and re.search(r"\bSwingUtilities\s*\.\s*invokeAndWait\s*\(", manager)
            and re.search(r"\bstartUp\s*\(", manager)):
        raise Refused("STARTUP_EDT_SEQUENCE_NOT_VERIFIED")

    basenames: dict[str, list[str]] = {}
    for name in sources:
        basenames.setdefault(name.rsplit("/", 1)[-1][:-5], []).append(name)

    plugin_files = [(name, text) for name, text in sorted(sources.items())
                    if name.startswith(PLUGIN_PREFIX) and EXTENDS.search(text)]
    if not plugin_files:
        raise Refused("PLUGIN_CLASSES_NOT_FOUND")

    detail = {}
    totals = Counter()
    without_override = []
    for path, source in plugin_files:
        klass = path.rsplit("/", 1)[-1][:-5]
        bodies = method_bodies(source, START)
        if len(bodies) > 1:
            raise Refused("DUPLICATE_STARTUP_OVERRIDE")
        if not bodies:
            without_override.append(klass)
            continue
        direct = set(indicators(bodies[0]))
        linked = set()
        resolved = set()
        for named in CONSTRUCT.findall(bodies[0]):
            matching = basenames.get(named, [])
            if len(matching) != 1:
                continue
            target = matching[0]
            if target == path:
                continue
            constructors = method_bodies(sources[target], constructor_pattern(named))
            if not constructors:
                continue
            resolved.add(named)
            for body in constructors:
                linked.update(indicators(body))

        for flag in direct:
            totals["direct_" + flag] += 1
        for flag in linked:
            totals["constructor_" + flag] += 1
        detail[klass] = {
            "direct_indicators": sorted(direct),
            "one_hop_constructor_indicators": sorted(linked),
            "one_hop_constructors_inspected": len(resolved),
            "potential_cleanup_path": ("cleanup" in direct or "cleanup" in linked),
            "potential_blocking_wait_path": ("wait" in direct or "wait" in linked),
            "potential_mutation_path": ("write" in direct or "write" in linked),
        }
    if len(detail) + len(without_override) != len(plugin_files):
        raise Refused("PLUGIN_ACCOUNTING_DRIFT")
    return {
        "status": "R393_STATIC_PLUGIN_STARTUP_RISK_INVENTORY",
        "plugin_subclass_count": len(plugin_files),
        "startup_override_count": len(detail),
        "without_explicit_startup_override": sorted(without_override),
        "startup_uses_swing_invoke_and_wait": True,
        "flagged_plugin_counts": dict(sorted(totals.items())),
        "per_plugin_evidence": detail,
        "one_hop_constructors_only": True,
        "lexical_evidence_not_reachability": True,
        "plugin_enablement_verified": False,
        "callback_or_async_execution_verified": False,
        "runtime_plugin_startup_executed": False,
        "client_executed": False,
        "freeze_root_cause_proven": False,
        "isolation_verified": False,
        "launch_authorized": False,
        "source_release_approved": False,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kit", type=Path, required=True)
    parser.add_argument("--kit-sha256", required=True)
    parser.add_argument("--expected-sources", type=int, default=1277)
    parser.add_argument("--out", type=Path)
    a = parser.parse_args(argv)
    try:
        pinned_archive(a.kit, a.kit_sha256)
        if a.out and (a.out.is_symlink() or a.out.exists()):
            raise Refused("REFUSE_EXISTING_OUTPUT")
        report = audit_sources(load_sources(a.kit, a.expected_sources))
        report["private_kit_sha256"] = a.kit_sha256
        rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
        if a.out:
            with a.out.open("x", encoding="utf-8") as f:
                f.write(rendered)
        else:
            print(rendered, end="")
        return 0
    except (Refused, OSError) as err:
        code = str(err) if isinstance(err, Refused) else "FILESYSTEM_FAILURE"
        print(json.dumps({"status": "R393_REFUSED", "reason": code}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

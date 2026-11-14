#!/usr/bin/env python3
"""R392: SHA-pinned, non-extracting prelaunch side-effect inventory.

This is a *static inventory* of recovered Java source in an owner-private kit.
It never executes a class, mounts a filesystem, opens a URL, or permits launch.
Aggregates counts only; does not expose source bodies, literal endpoints,
credentials, paths from source, or secret data.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import zipfile

MAX_KIT_BYTES = 64 * 1024 * 1024
MAX_SOURCE_BYTES = 5 * 1024 * 1024
MAX_TOTAL_SOURCE_BYTES = 150 * 1024 * 1024
EXPECTED_SOURCE_COUNT = 1277

# All expressions are source-text indicators, NOT Java interprocedural reachability.
FLAGS = {
    "home_directory_access": r'(?:System\.getProperty\s*\(\s*"user\.home"|System\.getenv\s*\()',
    "plugin_load": r"\bloadPlugins\s*\(",
    "plugin_start": r"\bstartPlugins\s*\(",
    "file_delete": r"(?:\.delete\s*\(|Files\.delete(?:IfExists)?\s*\()",
    "file_write": r"(?:new\s+(?:FileWriter|FileOutputStream|RandomAccessFile)\s*\(|Files\.(?:write|copy|move)\s*\()",
    "file_mkdir": r"(?:\.mkdirs?\s*\(|Files\.createDirector(?:y|ies)\s*\()",
    "network_connect": r"(?:new\s+(?:Socket|DatagramSocket)\s*\(|\.connect\s*\(|\.openConnection\s*\(|\.openStream\s*\()",
    "dns_local_host": r"\bInetAddress\.getLocalHost\s*\(",
    "process_execution": r"(?:Runtime\.getRuntime\s*\(\s*\)\s*\.exec\s*\(|new\s+ProcessBuilder\s*\()",
    "new_thread": r"(?:new\s+Thread\s*\(|\.startThread\s*\()",
}
RULES = {k: re.compile(v) for k, v in FLAGS.items()}
CRITICAL_FILES = {
    "launcher": "source/rs/gui/Launcher.java",
    "bootstrap": "source/rs/pkg42/Class255.java",
    "plugin_manager": "source/rs/plugins/PluginManager.java",
    "game_client": "source/rs/Client.java",
    "cache_updater": "source/rs/cache/updater/AssetUpdater.java",
    "file_downloader": "source/rs/cache/download/FileDownloader.java",
}
PIN = re.compile(r"[0-9a-f]{64}\Z")


class Refused(ValueError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_kit(path: Path, expected_sha256: str) -> None:
    if not PIN.fullmatch(expected_sha256):
        raise Refused("INVALID_SHA256_PIN")
    if path.is_symlink() or not path.is_file():
        raise Refused("KIT_NOT_REGULAR_FILE")
    if path.stat().st_size > MAX_KIT_BYTES:
        raise Refused("KIT_OVERSIZE")
    if sha256_file(path) != expected_sha256:
        raise Refused("KIT_HASH_MISMATCH")


def safe_archive_member(info: zipfile.ZipInfo) -> bool:
    name = info.filename
    parts = PurePosixPath(name).parts
    if not name or info.orig_filename != name or "\\" in name:
        return False
    if name.startswith("/") or name.startswith("//") or ":" in name:
        return False
    if any(part in ("", ".", "..") for part in name.split("/")):
        return False
    if info.create_system == 3 and stat.S_IFMT(info.external_attr >> 16) == stat.S_IFLNK:
        return False
    return all(part not in ("", ".", "..") for part in parts)


def inventory(kit: Path, expected_sources: int = EXPECTED_SOURCE_COUNT) -> dict:
    if expected_sources < 1 or expected_sources > 5000:
        raise Refused("INVALID_EXPECTED_SOURCE_COUNT")
    matching_files = Counter()
    matching_occurrences = Counter()
    critical = {key: {} for key in CRITICAL_FILES}
    source_count = 0
    expanded_total = 0
    seen = set()
    found_required = set()
    try:
        with zipfile.ZipFile(kit) as archive:
            for member in archive.infolist():
                if not safe_archive_member(member):
                    raise Refused("UNSAFE_ARCHIVE_MEMBER")
                if member.filename in seen:
                    raise Refused("DUPLICATE_ARCHIVE_MEMBER")
                seen.add(member.filename)
                if member.is_dir() or not member.filename.startswith("source/"):
                    continue
                if not member.filename.endswith(".java"):
                    continue
                if member.file_size > MAX_SOURCE_BYTES or member.file_size < 1:
                    raise Refused("SOURCE_SIZE_LIMIT")
                expanded_total += member.file_size
                if expanded_total > MAX_TOTAL_SOURCE_BYTES:
                    raise Refused("SOURCE_TOTAL_SIZE_LIMIT")
                source_count += 1
                raw = archive.read(member)
                if len(raw) != member.file_size:
                    raise Refused("SOURCE_SIZE_DRIFT")
                text = raw.decode("utf-8")
                file_flags = {}
                for flag, pattern in RULES.items():
                    count = len(pattern.findall(text))
                    file_flags[flag] = count
                    matching_occurrences[flag] += count
                    if count:
                        matching_files[flag] += 1
                for key, required_path in CRITICAL_FILES.items():
                    if member.filename == required_path:
                        found_required.add(key)
                        critical[key] = {flag: count for flag, count in file_flags.items()
                                         if count}
    except (zipfile.BadZipFile, UnicodeDecodeError, OSError, RuntimeError) as exc:
        raise Refused("KIT_SOURCE_SCAN_FAILED") from exc

    if source_count != expected_sources:
        raise Refused("SOURCE_COUNT_DRIFT")
    if len(found_required) != len(CRITICAL_FILES):
        raise Refused("CRITICAL_STARTUP_SOURCE_MISSING")
    return {
        "status": "R392_STATIC_PRELAUNCH_SIDE_EFFECT_INVENTORY",
        "source_count": source_count,
        "flagged_file_counts": dict(sorted(matching_files.items())),
        "flagged_source_occurrences": dict(sorted(matching_occurrences.items())),
        "startup_component_flags": critical,
        "evidence_is_lexical_only": True,
        "interprocedural_reachability_proven": False,
        "sandbox_verified": False,
        "network_egress_blocked_verified": False,
        "production_paths_isolated_verified": False,
        "actual_client_executed": False,
        "launch_authorized": False,
        "private_source_release_approved": False,
    }


def host_readonly_observation() -> dict:
    """Never treats presence of an executable as proof of an isolated guest."""
    if os.name != "nt":
        return {"platform": os.name, "sandbox_executable_present": None,
                "isolation_verified": False, "launch_authorized": False}
    root = Path(os.environ.get("SystemRoot", r"C:\Windows"))
    installed = (root / "System32" / "WindowsSandbox.exe").is_file()
    return {"platform": "windows", "sandbox_executable_present": installed,
            "isolation_verified": False, "launch_authorized": False}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kit", type=Path, required=True)
    parser.add_argument("--kit-sha256", required=True)
    parser.add_argument("--expected-sources", type=int, default=EXPECTED_SOURCE_COUNT)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    try:
        verify_kit(args.kit, args.kit_sha256)
        if args.out and (args.out.exists() or args.out.is_symlink()):
            raise Refused("REFUSE_EXISTING_OUTPUT")
        report = inventory(args.kit, args.expected_sources)
        report["private_kit_sha256"] = args.kit_sha256
        report["host_observation"] = host_readonly_observation()
        rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
        if args.out:
            with args.out.open("x", encoding="utf-8") as f:
                f.write(rendered)
        else:
            print(rendered, end="")
        return 0
    except Refused as exc:
        print(json.dumps({"status": "R392_REFUSED", "reason": str(exc)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

"""Fetch exact SHA-256-pinned public decompiler JARs without executing them.

Only fixed official Maven Central artifact URLs are allowed. An independently
supplied full artifact hash is mandatory. Neither client JAR nor source is read.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from typing import Any
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from zipfile import BadZipFile, ZipFile


class DecompilerArtifactError(ValueError):
    """Remote decompiler tool artifact was not safely acquired."""


_TOOL_URLS = {
    "cfr": "https://repo.maven.apache.org/maven2/org/benf/cfr/0.152/cfr-0.152.jar",
    "vineflower": (
        "https://repo.maven.apache.org/maven2/org/vineflower/vineflower/"
        "1.10.1/vineflower-1.10.1.jar"
    ),
}
_MAX_BYTES = 32 * 1024 * 1024


def _require(ok: bool, reason: str) -> None:
    if not ok:
        raise DecompilerArtifactError(reason)


def _verify_executable_jar(path: Path) -> None:
    try:
        with ZipFile(path) as archive:
            members = archive.infolist()
            _require(
                any(i.filename.endswith(".class") and not i.is_dir()
                    for i in members),
                "DOWNLOADED_JAR_HAS_NO_CLASSES",
            )
            manifest = [i for i in members
                        if i.filename.upper() == "META-INF/MANIFEST.MF"]
            _require(len(manifest) == 1, "DOWNLOADED_JAR_MANIFEST_NOT_UNIQUE")
            _require(manifest[0].file_size <= 65536,
                     "DOWNLOADED_JAR_MANIFEST_TOO_LARGE")
            content = archive.read(manifest[0]).decode("utf-8", errors="replace")
            _require(
                re.search(r"(?im)^Main-Class:\s*\S+", content) is not None,
                "DOWNLOADED_JAR_NOT_DIRECTLY_EXECUTABLE",
            )
    except (BadZipFile, OSError, EOFError):
        raise DecompilerArtifactError("DOWNLOADED_JAR_INVALID") from None


def acquire_decompiler_jar(
    engine: str, destination: Path, *, expected_sha256: str,
    timeout_seconds: int = 45,
) -> dict[str, Any]:
    """Read only a fixed HTTPS Maven URL; never overwrite or run a binary."""
    _require(engine in _TOOL_URLS, "UNSUPPORTED_DECOMPILER_ENGINE")
    _require(
        isinstance(expected_sha256, str)
        and re.fullmatch(r"[0-9a-fA-F]{64}", expected_sha256) is not None,
        "MISSING_OR_INVALID_INDEPENDENT_TOOL_SHA256",
    )
    _require(
        type(timeout_seconds) is int and 1 <= timeout_seconds <= 120,
        "INVALID_ARTIFACT_NETWORK_TIMEOUT",
    )
    dest = Path(destination)
    _require(not dest.exists() and not dest.is_symlink(),
             "DECOMPILER_OUTPUT_ALREADY_EXISTS")
    url = _TOOL_URLS[engine]
    parsed = urlparse(url)
    _require(
        parsed.scheme == "https" and parsed.hostname == "repo.maven.apache.org",
        "UNTRUSTED_ARTIFACT_ORIGIN",
    )
    dest.parent.mkdir(parents=True, exist_ok=True)
    created = False
    try:
        try:
            with dest.open("xb") as target:
                created = True
                req = Request(
                    url, headers={"User-Agent": "SpawnPK-Client-source-recovery/1"},
                )
                try:
                    with urlopen(req, timeout=timeout_seconds) as response:
                        effective = urlparse(response.geturl())
                        _require(
                            effective.scheme == "https"
                            and effective.hostname == "repo.maven.apache.org"
                            and response.geturl() == url,
                            "DECOMPILER_ARTIFACT_REDIRECTED",
                        )
                        total = 0
                        digest = hashlib.sha256()
                        while True:
                            chunk = response.read(65536)
                            if not chunk:
                                break
                            total += len(chunk)
                            _require(total <= _MAX_BYTES,
                                     "DECOMPILER_ARTIFACT_EXCEEDS_SIZE_LIMIT")
                            digest.update(chunk)
                            target.write(chunk)
                except (URLError, TimeoutError, OSError):
                    raise DecompilerArtifactError(
                        "DECOMPILER_ARTIFACT_NETWORK_FAILURE"
                    ) from None
        except FileExistsError:
            # File existed after preflight; never remove a competing file.
            raise DecompilerArtifactError("DECOMPILER_OUTPUT_ALREADY_EXISTS") from None

        _require(digest.hexdigest() == expected_sha256.lower(),
                 "DECOMPILER_ARTIFACT_SHA256_MISMATCH")
        _verify_executable_jar(dest)
        return {
            "schema_version": 1,
            "kind": "independently_pinned_decompiler_artifact",
            "engine": engine,
            "url": url,
            "sha256": digest.hexdigest(),
            "size_bytes": total,
            "validated_executable_jar": True,
            "client_source_touched": False,
            "canonical_mapping_promoted": False,
        }
    except Exception:
        if created:
            dest.unlink(missing_ok=True)
        raise


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("engine", choices=sorted(_TOOL_URLS))
    p.add_argument("destination", type=Path)
    p.add_argument("--sha256", required=True)
    p.add_argument("--timeout-seconds", type=int, default=45)
    args = p.parse_args(argv)
    try:
        result = acquire_decompiler_jar(
            args.engine, args.destination,
            expected_sha256=args.sha256,
            timeout_seconds=args.timeout_seconds,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
    except DecompilerArtifactError as exc:
        p.error(str(exc))
    except (OSError, ValueError):
        p.error("DECOMPILER_ARTIFACT_ACQUISITION_FAILED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

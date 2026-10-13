"""R123: read-only private multi-module source ZIP delta; no source publication.

Compares uploaded source with the previously recovered private Java candidate.
Does not execute archive contents or certify original-client/server equivalence.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile


class PrivateArchiveDeltaError(ValueError):
    pass


def require(condition, why):
    if not condition:
        raise PrivateArchiveDeltaError(why)


def fingerprint(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def safe_entries(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(),
            "PRIVATE_SOURCE_ZIP_REQUIRED")
    with ZipFile(path) as archive:
        infos = archive.infolist()
        require(1 <= len(infos) <= 50000, "ZIP_ENTRY_COUNT_OUT_OF_RANGE")
        names = []
        total = 0
        for info in infos:
            name = info.filename
            require(not name.startswith("/") and "\\" not in name
                    and all(p not in ("", ".", "..")
                            for p in name.rstrip("/").split("/")),
                    "ZIP_ENTRY_UNSAFE_PATH")
            require(((info.external_attr >> 16) & 0o170000) != 0o120000,
                    "ZIP_SYMLINK_NOT_ALLOWED")
            require(info.file_size <= 64 * 1024 * 1024,
                    "ZIP_ENTRY_TOO_LARGE")
            total += info.file_size
            require(total <= 1024 * 1024 * 1024,
                    "ZIP_UNCOMPRESSED_TOTAL_TOO_LARGE")
            names.append(name)
        require(len(names) == len(set(names)), "ZIP_DUPLICATE_ENTRY")
        roots = {name.split("/")[0] for name in names}
        require(len(roots) == 1, "EXACTLY_ONE_SOURCE_ARCHIVE_ROOT_REQUIRED")
        root = next(iter(roots)) + "/"
        rels = {name[len(root):]: name for name in names
                if name != root and not name.endswith("/")}
        return {rel: hashlib.sha256(archive.read(real)).hexdigest()
                for rel, real in rels.items()}


def audit(uploaded_archive, baseline_archive):
    current = safe_entries(uploaded_archive)
    previous = safe_entries(baseline_archive)
    candidate = {
        k[len("client/src/main/java/"):]: v for k, v in current.items()
        if k.startswith("client/src/main/java/") and k.endswith(".java")
    }
    baseline = {
        k[len("src/main/java/"):]: v for k, v in previous.items()
        if k.startswith("src/main/java/") and k.endswith(".java")
    }
    require(candidate and baseline, "CLIENT_JAVA_SOURCE_BASELINE_REQUIRED")
    shared = set(candidate) & set(baseline)
    changed = sorted(k for k in shared if candidate[k] != baseline[k])
    added = sorted(set(candidate) - set(baseline))
    removed = sorted(set(baseline) - set(candidate))
    server_main = sorted(k for k in current if k.startswith("server/")
                         and "/src/main/java/" in k and k.endswith(".java"))
    server_tests = sorted(k for k in current if k.startswith("server/")
                          and "/src/test/java/" in k and k.endswith(".java"))
    main_by_module = Counter(
        k.split("/src/main/java/")[0] for k in server_main
    )
    test_by_module = Counter(
        k.split("/src/test/java/")[0] for k in server_tests
    )
    expected = {
        "gradle_wrapper_jar": "gradle/wrapper/gradle-wrapper.jar",
        "vendored_client_dependency": "client/libs/vendored-unidentified.jar",
        "gradle_wrapper_script": "gradlew",
        "server_gradle": "server/build.gradle",
        "client_gradle": "client/build.gradle",
    }
    return {
        "schema_version": 1,
        "kind": "private_decompiled_multimodule_source_archive_delta_r123",
        "uploaded_archive_sha256": fingerprint(uploaded_archive),
        "baseline_archive_sha256": fingerprint(baseline_archive),
        "uploaded_files": len(current),
        "baseline_files": len(previous),
        "uploaded_java_total": sum(k.endswith(".java") for k in current),
        "client_java_source_files": len(candidate),
        "baseline_client_java_source_files": len(baseline),
        "shared_client_java_files": len(shared),
        "byte_identical_shared_client_java_files":
            sum(candidate[k] == baseline[k] for k in shared),
        "changed_client_java_files": changed,
        "new_client_java_files": added,
        "baseline_only_client_java_files": removed,
        "server_main_java_files": len(server_main),
        "server_test_java_files": len(server_tests),
        "server_main_java_by_module": dict(sorted(main_by_module.items())),
        "server_test_java_by_module": dict(sorted(test_by_module.items())),
        "build_inputs_present": {
            key: value in current for key, value in expected.items()
        },
        "original_v309_parity_certified": False,
        "server_original_source_certified": False,
        "source_executed": False,
        "publish_client_or_server_source_to_git": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("uploaded_archive")
    parser.add_argument("older_source_archive")
    parser.add_argument("new_private_report")
    args = parser.parse_args(argv)
    dest = Path(args.new_private_report)
    try:
        require(not dest.exists() and not dest.is_symlink()
                and dest.parent.is_dir(), "PRIVATE_REPORT_MUST_NOT_EXIST")
        report = audit(args.uploaded_archive, args.older_source_archive)
        dest.write_text(
            json.dumps(report, sort_keys=True, indent=2) + "\n",
            encoding="utf-8"
        )
        print(json.dumps(report, sort_keys=True))
    except Exception:
        parser.error("PRIVATE_DECOMPILED_SOURCE_ARCHIVE_R123_NOT_ACCEPTED")


if __name__ == "__main__":
    main()

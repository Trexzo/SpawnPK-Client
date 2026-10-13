"""R124: strict read-only v308/v309 original-client and runtime-assets inventory.

The canonical original client JARs and cache ZIP stay local. The report includes
only SHA pins, counts, aggregated resource categories and source-reuse deltas.
It NEVER serializes user profile paths, logs, account IDs, source or binaries.
"""
from __future__ import annotations

from collections import Counter
import argparse
import hashlib
import io
import json
from pathlib import Path
from zipfile import ZipFile

V308 = "854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6"
V309 = "ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38"
NAMES = {
    "v308": ".spawnpk-data/client-v308.jar",
    "v309": ".spawnpk-data/client.jar",
}


class PrivateClientAssetDeltaR124Error(ValueError):
    pass


def need(ok, reason):
    if not ok:
        raise PrivateClientAssetDeltaR124Error(reason)


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _files(archive, *, max_files=18000):
    infos = archive.infolist()
    need(0 < len(infos) <= max_files, "ARCHIVE_ENTRY_COUNT_INVALID")
    names = set()
    for info in infos:
        n = info.filename
        need(not n.startswith("/") and "\\" not in n
             and all(x not in ("", ".", "..") for x in n.rstrip("/").split("/")),
             "UNSAFE_ARCHIVE_MEMBER_PATH")
        need(((info.external_attr >> 16) & 0o170000) != 0o120000,
             "ARCHIVE_SYMLINK_NOT_ALLOWED")
        need(n not in names, "DUPLICATE_ARCHIVE_MEMBER")
        need(info.file_size <= 150 * 1024 * 1024,
             "ARCHIVE_MEMBER_TOO_LARGE")
        names.add(n)
    return infos


def _inner_jar_inventory(blob):
    with ZipFile(io.BytesIO(blob)) as z:
        infos = _files(z, max_files=16000)
        classes = {}
        resources = 0
        for info in infos:
            if info.is_dir():
                continue
            if info.filename.endswith(".class"):
                classes[info.filename] = _sha(z.read(info))
            else:
                resources += 1
    return classes, resources


def _by_region(paths):
    return {
        "game_rs": {x for x in paths if x.startswith("rs/") and x.endswith(".class")},
        "other_classes": {x for x in paths if not x.startswith("rs/") and x.endswith(".class")},
    }


def _delta(old, new, paths):
    before = {x for x in old if x in paths}
    after = {x for x in new if x in paths}
    common = before & after
    stable = sum(old[x] == new[x] for x in common)
    return {
        "old": len(before),
        "new": len(after),
        "same_path": len(common),
        "byte_identical_same_path": stable,
        "modified_same_path": len(common) - stable,
        "new_paths": len(after - before),
        "removed_paths": len(before - after),
        "same_path_byte_reuse_percent_of_new":
            round(100 * stable / len(after), 2) if after else 0,
    }


def inventory_private_original_assets(bundle, *, expected=None):
    expected = expected if expected is not None else {"v308": V308, "v309": V309}
    source = Path(bundle)
    need(source.is_file() and not source.is_symlink(),
         "PRIVATE_ASSET_ARCHIVE_FILE_REQUIRED")
    with ZipFile(source) as outer:
        infos = _files(outer)
        names = [x.filename for x in infos if not x.is_dir()]
        need(all(names.count(v) == 1 for v in NAMES.values()),
             "EXACT_CANONICAL_CLIENT_JAR_PAIR_REQUIRED")
        originals = {}
        for version, member in NAMES.items():
            blob = outer.read(member)
            need(_sha(blob) == expected[version],
                 "ORIGINAL_" + version.upper() + "_SHA256_MISMATCH")
            classes, resources = _inner_jar_inventory(blob)
            originals[version] = {
                "sha256": _sha(blob),
                "jar_bytes": len(blob),
                "classes": classes,
                "other_resources": resources,
            }

        selected = [x for x in infos
                    if not x.is_dir() and x.filename.startswith(".spawnpk/")]
        groups = Counter()
        totals = Counter()
        # Content fingerprints are private, but the combined fingerprint is
        # safe to publish because no private member names or values are exposed.
        asset_manifest = hashlib.sha256()
        for info in sorted(selected, key=lambda x: x.filename):
            parts = info.filename.split("/")
            category = parts[1] if len(parts) > 1 else "other"
            groups[category] += 1
            totals[category] += info.file_size
            content_hash = hashlib.sha256()
            with outer.open(info) as file:
                for chunk in iter(lambda: file.read(1024 * 1024), b""):
                    content_hash.update(chunk)
            asset_manifest.update(info.filename.encode("utf-8") + b"\0")
            asset_manifest.update(content_hash.digest())

        personal = [x for x in names
                    if x.startswith(".spawnpk-data/") and
                    x not in set(NAMES.values())]
        old = originals["v308"]["classes"]
        new = originals["v309"]["classes"]
        regions = _by_region(set(old) | set(new))
        total_diff = _delta(old, new, set(old) | set(new))
        return {
            "schema_version": 1,
            "kind": "private_client_v308_v309_class_delta_and_assets_r124",
            "exact_original_binary_authority": True,
            "original_builds": {
                v: {
                    "jar_sha256": originals[v]["sha256"],
                    "jar_bytes": originals[v]["jar_bytes"],
                    "classfile_count": len(originals[v]["classes"]),
                    "nonclass_resource_count": originals[v]["other_resources"],
                } for v in ("v308", "v309")
            },
            "binary_class_delta": {
                **{key: _delta(old, new, region)
                   for key, region in regions.items()},
                "all_classes": total_diff,
            },
            "runtime_asset_files": len(selected),
            "runtime_asset_total_bytes": sum(x.file_size for x in selected),
            "runtime_asset_group_files": dict(sorted(groups.items())),
            "runtime_asset_group_bytes": dict(sorted(totals.items())),
            "runtime_asset_sha256_manifest": asset_manifest.hexdigest(),
            "local_profile_files_excluded": len(personal),
            "profile_or_account_settings_published": False,
            "original_jars_published": False,
            "cache_or_sprite_binaries_published": False,
            "full_deobfuscated_source_tree_accepted": False,
            "runtime_equivalence_proven": False,
            "note": (
                "Byte-identical classfiles at stable paths are candidates "
                "for source carry-forward, not proof of semantic identity "
                "for changed/renamed classes or dependency-compatible javac."
            ),
        }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private_assets_zip")
    parser.add_argument("new_private_report_json")
    args = parser.parse_args(argv)
    out = Path(args.new_private_report_json)
    try:
        need(not out.exists() and not out.is_symlink()
             and out.parent.is_dir() and not out.parent.is_symlink(),
             "REPORT_OUTPUT_MUST_BE_FRESH")
        report = inventory_private_original_assets(args.private_assets_zip)
        out.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n",
                       encoding="utf-8")
        print("PRIVATE_CLIENT_ASSET_AND_V308_V309_CLASS_DELTA_R124_PASS")
        print("report_sha256=" + _sha(out.read_bytes()))
    except Exception:
        parser.error("PRIVATE_V308_V309_CLIENT_ASSET_DELTA_NOT_ACCEPTED")


if __name__ == "__main__":
    main()

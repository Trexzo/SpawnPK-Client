from __future__ import annotations

from collections import defaultdict


def diff_indexes(old: dict, new: dict) -> dict:
    old_entries = old["entries"]
    new_entries = new["entries"]
    old_paths, new_paths = set(old_entries), set(new_entries)
    exact_same = sorted(p for p in old_paths & new_paths if old_entries[p]["sha256"] == new_entries[p]["sha256"])
    changed_same_path = sorted(p for p in old_paths & new_paths if old_entries[p]["sha256"] != new_entries[p]["sha256"])
    added = sorted(new_paths - old_paths)
    removed = sorted(old_paths - new_paths)

    # Name-insensitive class fingerprint transfer candidates.
    old_by_fp: dict[str, list[str]] = defaultdict(list)
    new_by_fp: dict[str, list[str]] = defaultdict(list)
    for p, c in old.get("classes", {}).items():
        old_by_fp[c["structural_sha256"]].append(p)
    for p, c in new.get("classes", {}).items():
        new_by_fp[c["structural_sha256"]].append(p)

    structural_unique = []
    structural_ambiguous = []
    for fp in sorted(set(old_by_fp) & set(new_by_fp)):
        o, n = old_by_fp[fp], new_by_fp[fp]
        if len(o) == 1 and len(n) == 1:
            if o[0] != n[0]:
                structural_unique.append({"old": o[0], "new": n[0], "fingerprint": fp})
        elif set(o) != set(n):
            structural_ambiguous.append({"old": sorted(o), "new": sorted(n), "fingerprint": fp})

    return {
        "schema_version": 1,
        "old_sha256": old["sha256"],
        "new_sha256": new["sha256"],
        "summary": {
            "exact_unchanged_entries": len(exact_same),
            "changed_same_path_entries": len(changed_same_path),
            "added_entries": len(added),
            "removed_entries": len(removed),
            "unique_structural_class_moves": len(structural_unique),
            "ambiguous_structural_groups": len(structural_ambiguous),
        },
        "exact_unchanged": exact_same,
        "changed_same_path": changed_same_path,
        "added": added,
        "removed": removed,
        "unique_structural_class_moves": structural_unique,
        "ambiguous_structural_groups": structural_ambiguous,
    }

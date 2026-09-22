from __future__ import annotations

from collections import defaultdict
from typing import Any

from .confidence import MatchThresholds, confidence_label
from .evidence import candidate_shape_compatible, class_evidence


def _scope(index: dict, prefix: str | None) -> dict[str, dict]:
    classes = index.get("classes", {})
    if prefix is None:
        return dict(classes)
    return {
        path: value
        for path, value in classes.items()
        if path.startswith(prefix)
    }


def _unique_by(values: dict[str, dict], key_fn) -> dict[Any, str]:
    buckets: dict[Any, list[str]] = defaultdict(list)
    for path, value in values.items():
        key = key_fn(path, value)
        if key is not None:
            buckets[key].append(path)
    return {
        key: paths[0]
        for key, paths in buckets.items()
        if len(paths) == 1
    }


def _match_record(
    old_path: str,
    new_path: str,
    strategy: str,
    score: float,
    evidence: dict,
) -> dict:
    return {
        "old": old_path,
        "new": new_path,
        "strategy": strategy,
        "score": round(float(score), 6),
        "confidence": confidence_label(score, strategy),
        "evidence": evidence,
    }


def _package_prefix(path: str) -> str:
    parts = path.split("/")
    return "/".join(parts[:2]) if len(parts) >= 2 else path


def _infer_package_anchors(
    matches: list[dict],
    thresholds: MatchThresholds,
) -> dict[str, dict]:
    pair_counts: dict[tuple[str, str], int] = defaultdict(int)
    source_counts: dict[str, int] = defaultdict(int)

    for match in matches:
        if (
            match.get("strategy") != "structural_unique"
            or match["old"] == match["new"]
        ):
            continue
        old_prefix = _package_prefix(match["old"])
        new_prefix = _package_prefix(match["new"])
        if old_prefix == new_prefix:
            continue
        pair_counts[(old_prefix, new_prefix)] += 1
        source_counts[old_prefix] += 1

    candidates: dict[str, list[tuple[str, int, float]]] = defaultdict(list)
    for (old_prefix, new_prefix), support in pair_counts.items():
        dominance = support / source_counts[old_prefix]
        if (
            support >= thresholds.package_anchor_min_support
            and dominance >= thresholds.package_anchor_min_dominance
        ):
            candidates[old_prefix].append(
                (new_prefix, support, dominance)
            )

    anchors = {}
    for old_prefix, rows in candidates.items():
        rows.sort(key=lambda r: (-r[1], -r[2], r[0]))
        new_prefix, support, dominance = rows[0]
        anchors[old_prefix] = {
            "new_prefix": new_prefix,
            "support": support,
            "dominance": round(dominance, 6),
        }
    return anchors


def match_classes(
    old_index: dict,
    new_index: dict,
    *,
    prefix: str | None = "rs/",
    thresholds: MatchThresholds | None = None,
    ambiguous_limit: int = 5,
) -> dict:
    """Conservative cross-build identity matching.

    Stages:
      1. Unique exact entry SHA-256.
      2. Unique name-insensitive structural fingerprint.
      3. Strong package-migration anchors inferred only from stage-2 matches.
      4. Mutual-best weighted evidence with score and margin gates.

    Low-confidence or tied candidates are deliberately left unresolved.
    """
    thresholds = thresholds or MatchThresholds()
    old_classes = _scope(old_index, prefix)
    new_classes = _scope(new_index, prefix)
    remaining_old = set(old_classes)
    remaining_new = set(new_classes)
    matches: list[dict] = []

    old_sha = _unique_by(
        old_classes,
        lambda path, _: old_index.get("entries", {})
        .get(path, {})
        .get("sha256"),
    )
    new_sha = _unique_by(
        new_classes,
        lambda path, _: new_index.get("entries", {})
        .get(path, {})
        .get("sha256"),
    )
    for sha in sorted(set(old_sha) & set(new_sha)):
        old_path, new_path = old_sha[sha], new_sha[sha]
        if old_path not in remaining_old or new_path not in remaining_new:
            continue
        ev = class_evidence(
            old_index,
            old_path,
            old_classes[old_path],
            new_index,
            new_path,
            new_classes[new_path],
        )
        matches.append(
            _match_record(
                old_path,
                new_path,
                "exact_sha256",
                thresholds.exact_score,
                ev,
            )
        )
        remaining_old.remove(old_path)
        remaining_new.remove(new_path)

    old_fp = _unique_by(
        {p: old_classes[p] for p in remaining_old},
        lambda _path, c: c.get("structural_sha256"),
    )
    new_fp = _unique_by(
        {p: new_classes[p] for p in remaining_new},
        lambda _path, c: c.get("structural_sha256"),
    )
    for fp in sorted(set(old_fp) & set(new_fp)):
        old_path, new_path = old_fp[fp], new_fp[fp]
        if old_path not in remaining_old or new_path not in remaining_new:
            continue
        ev = class_evidence(
            old_index,
            old_path,
            old_classes[old_path],
            new_index,
            new_path,
            new_classes[new_path],
        )
        matches.append(
            _match_record(
                old_path,
                new_path,
                "structural_unique",
                thresholds.structural_score,
                ev,
            )
        )
        remaining_old.remove(old_path)
        remaining_new.remove(new_path)

    package_anchors = _infer_package_anchors(matches, thresholds)
    for old_path in sorted(list(remaining_old)):
        old_prefix = _package_prefix(old_path)
        anchor = package_anchors.get(old_prefix)
        if not anchor:
            continue

        suffix = old_path[len(old_prefix):]
        new_path = anchor["new_prefix"] + suffix
        if new_path not in remaining_new:
            continue

        old_class = old_classes[old_path]
        new_class = new_classes[new_path]
        if not candidate_shape_compatible(old_class, new_class):
            continue

        ev = class_evidence(
            old_index,
            old_path,
            old_class,
            new_index,
            new_path,
            new_class,
        )
        if (
            ev["score"] < thresholds.package_anchor_min_score
            or ev["evidence_weight"]
            < thresholds.package_anchor_min_evidence_weight
        ):
            continue

        ev = dict(ev)
        ev["package_anchor"] = {
            "old_prefix": old_prefix,
            "new_prefix": anchor["new_prefix"],
            "support": anchor["support"],
            "dominance": anchor["dominance"],
        }
        matches.append(
            _match_record(
                old_path,
                new_path,
                "package_anchor",
                ev["score"],
                ev,
            )
        )
        remaining_old.remove(old_path)
        remaining_new.remove(new_path)

    ranked_old: dict[str, list[dict]] = {}
    ranked_new: dict[str, list[dict]] = defaultdict(list)
    for old_path in sorted(remaining_old):
        old_class = old_classes[old_path]
        candidates: list[dict] = []
        for new_path in sorted(remaining_new):
            new_class = new_classes[new_path]
            if not candidate_shape_compatible(old_class, new_class):
                continue
            ev = class_evidence(
                old_index,
                old_path,
                old_class,
                new_index,
                new_path,
                new_class,
            )
            candidates.append(
                {
                    "path": new_path,
                    "score": ev["score"],
                    "evidence_weight": ev["evidence_weight"],
                    "evidence": ev,
                }
            )
            ranked_new[new_path].append(
                {
                    "path": old_path,
                    "score": ev["score"],
                    "evidence_weight": ev["evidence_weight"],
                }
            )

        candidates.sort(
            key=lambda c: (
                -c["score"],
                -c["evidence_weight"],
                c["path"],
            )
        )
        ranked_old[old_path] = candidates

    for candidates in ranked_new.values():
        candidates.sort(
            key=lambda c: (
                -c["score"],
                -c["evidence_weight"],
                c["path"],
            )
        )

    ambiguous: list[dict] = []
    weighted_pairs: list[tuple[str, str, dict]] = []
    for old_path in sorted(remaining_old):
        candidates = ranked_old.get(old_path, [])
        if not candidates:
            continue

        best = candidates[0]
        runner_score = (
            candidates[1]["score"]
            if len(candidates) > 1
            else 0.0
        )
        margin = best["score"] - runner_score
        reverse = ranked_new.get(best["path"], [])
        reverse_best = reverse[0]["path"] if reverse else None

        qualifies = (
            best["score"] >= thresholds.minimum_score
            and best["evidence_weight"]
            >= thresholds.minimum_evidence_weight
            and margin >= thresholds.minimum_margin
            and reverse_best == old_path
        )
        if qualifies:
            weighted_pairs.append(
                (old_path, best["path"], best)
            )
        elif best["score"] >= thresholds.minimum_score:
            ambiguous.append(
                {
                    "old": old_path,
                    "reason": "weighted_match_not_decisive",
                    "best_score": round(
                        float(best["score"]),
                        6,
                    ),
                    "margin": round(float(margin), 6),
                    "mutual_best": reverse_best == old_path,
                    "candidates": [
                        {
                            "new": c["path"],
                            "score": round(
                                float(c["score"]),
                                6,
                            ),
                            "evidence_weight": round(
                                float(c["evidence_weight"]),
                                6,
                            ),
                        }
                        for c in candidates[:ambiguous_limit]
                    ],
                }
            )

    used_old: set[str] = set()
    used_new: set[str] = set()
    for old_path, new_path, best in sorted(
        weighted_pairs,
        key=lambda item: (
            -item[2]["score"],
            item[0],
            item[1],
        ),
    ):
        if old_path in used_old or new_path in used_new:
            continue
        matches.append(
            _match_record(
                old_path,
                new_path,
                "weighted_mutual_best",
                best["score"],
                best["evidence"],
            )
        )
        used_old.add(old_path)
        used_new.add(new_path)

    matched_old = {m["old"] for m in matches}
    matched_new = {m["new"] for m in matches}
    unresolved_old = sorted(
        set(old_classes) - matched_old
    )
    unresolved_new = sorted(
        set(new_classes) - matched_new
    )
    matches.sort(
        key=lambda m: (m["old"], m["new"])
    )

    strategies: dict[str, int] = defaultdict(int)
    for match in matches:
        strategies[match["strategy"]] += 1

    return {
        "schema_version": 1,
        "old_sha256": old_index.get("sha256"),
        "new_sha256": new_index.get("sha256"),
        "scope_prefix": prefix,
        "thresholds": {
            "minimum_score": thresholds.minimum_score,
            "minimum_margin": thresholds.minimum_margin,
            "minimum_evidence_weight":
                thresholds.minimum_evidence_weight,
            "package_anchor_min_support":
                thresholds.package_anchor_min_support,
            "package_anchor_min_dominance":
                thresholds.package_anchor_min_dominance,
            "package_anchor_min_score":
                thresholds.package_anchor_min_score,
            "package_anchor_min_evidence_weight":
                thresholds.package_anchor_min_evidence_weight,
        },
        "package_anchors": package_anchors,
        "summary": {
            "old_class_count": len(old_classes),
            "new_class_count": len(new_classes),
            "matched": len(matches),
            "exact_sha256": strategies["exact_sha256"],
            "structural_unique":
                strategies["structural_unique"],
            "package_anchor":
                strategies["package_anchor"],
            "weighted_mutual_best":
                strategies["weighted_mutual_best"],
            "ambiguous": len(ambiguous),
            "unmatched_old": len(unresolved_old),
            "unmatched_new": len(unresolved_new),
        },
        "matches": matches,
        "ambiguous": sorted(
            ambiguous,
            key=lambda x: x["old"],
        ),
        "unmatched_old": unresolved_old,
        "unmatched_new": unresolved_new,
    }

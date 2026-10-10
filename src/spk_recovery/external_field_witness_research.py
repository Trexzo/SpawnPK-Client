"""Read-only, external canonical-method witnesses for unresolved JVM fields.

Unlike R3M field_proof, this never applies or mutates canonical field lineage.
Generated reports contain private JVM coordinates and must remain local.
"""
from __future__ import annotations

from collections import defaultdict
import hashlib
import json
from pathlib import Path
from typing import Any
from zipfile import ZipFile

from .bytecode_profile import profile_class_field_accesses
from .field_proof import _build, _class_entries
from .indexer import sha256_file
from .lineage import validate_lineage
from .member_lineage import validate_member_lineage


class ExternalWitnessError(ValueError):
    pass


def _require(ok: bool, message: str) -> None:
    if not ok:
        raise ExternalWitnessError(message)


def _digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _method_rows(members: dict, old_build_id: str, new_build_id: str):
    for row in members.get("members", []):
        if row.get("kind") != "method":
            continue
        old = [x for x in row.get("lineage", []) if x.get("build_id") == old_build_id]
        new = [x for x in row.get("lineage", []) if x.get("build_id") == new_build_id]
        _require(len(old) <= 1 and len(new) <= 1, "DUPLICATE_METHOD_BUILD_RELATION")
        if len(old) == len(new) == 1:
            yield row["member_id"], row["owner_logical_id"], old[0], new[0]


def _candidate_fields(member_lineage: dict, old_build_id: str, new_build_id: str,
                      class_id: str, old_owner: str, new_owner: str) -> list[dict]:
    by_old: dict[tuple[str, str], dict] = {}
    accepted_new: set[tuple[str, str, str]] = set()
    for rec in member_lineage.get("members", []):
        if rec.get("kind") != "field":
            continue
        old = [v for v in rec.get("lineage", []) if v.get("build_id") == old_build_id]
        new = [v for v in rec.get("lineage", []) if v.get("build_id") == new_build_id]
        _require(len(old) <= 1 and len(new) <= 1, "DUPLICATE_FIELD_RELATION")
        for item in new:
            accepted_new.add((item["owner_internal_name"], item["name"], item["descriptor"]))
        if rec.get("owner_logical_id") == class_id and old:
            _require(old[0]["owner_internal_name"] == old_owner, "OLD_FIELD_OWNER_NOT_CANONICAL")
            key = (old[0]["name"], old[0]["descriptor"])
            _require(key not in by_old, "DUPLICATE_OLD_FIELD")
            by_old[key] = {"id": rec["member_id"], "old": old[0], "already_new": bool(new)}

    candidates = []
    observed_old = set()
    observed_new = set()
    for u in member_lineage.get("unresolved", []):
        if u.get("kind") != "member_identity_review" or u.get("member_kind") != "field" or u.get("new_build_id") != new_build_id:
            continue
        c = u.get("candidate", {})
        if not isinstance(c, dict) or str(c.get("old_owner", "")).removesuffix(".class") != old_owner:
            continue
        _require(str(c.get("new_owner", "")).removesuffix(".class") == new_owner, "UNRESOLVED_OWNER_CONFLICT")
        a, b = c.get("old"), c.get("new")
        _require(isinstance(a, dict) and isinstance(b, dict), "MALFORMED_FIELD_CANDIDATE")
        ok = (a.get("name"), a.get("descriptor"))
        nk = (b.get("name"), b.get("descriptor"))
        _require(ok in by_old, "UNRESOLVED_FIELD_LACKS_CANONICAL_BASELINE")
        _require(not by_old[ok]["already_new"], "FIELD_ALREADY_ACCEPTED")
        _require((new_owner, *nk) not in accepted_new, "TARGET_ALREADY_ASSIGNED")
        _require(ok not in observed_old and nk not in observed_new, "AMBIGUOUS_FIELD_CANDIDATE")
        observed_old.add(ok)
        observed_new.add(nk)
        candidates.append({
            "member_id": by_old[ok]["id"],
            "old": {"name": ok[0], "descriptor": ok[1]},
            "new": {"name": nk[0], "descriptor": nk[1]},
            "old_access": by_old[ok]["old"].get("access"),
        })
    return sorted(candidates, key=lambda x: x["member_id"])


def _find_method(profile: dict, record: dict) -> dict:
    matches = [v for v in profile.get("methods", [])
               if v.get("name") == record.get("name") and v.get("descriptor") == record.get("descriptor")]
    _require(len(matches) == 1, "CANONICAL_METHOD_DECLARATION_NOT_UNIQUE")
    found = matches[0]
    _require(found.get("access") == record.get("access"), "CANONICAL_METHOD_ACCESS_CHANGED")
    _require(found.get("code_length") is not None, "CANONICAL_METHOD_HAS_NO_CODE")
    _require(found.get("code_length") == record.get("code_length"), "CANONICAL_METHOD_CODE_LENGTH_MISMATCH")
    return found


# Symbolic CP operands may be renamed independently of their bytecode.
# Check every other decoder-owned instruction operand rather than only the
# opcode/offset skeleton (which misses altered locals, branches and iinc).
_SYMBOLIC_CP_FIELDS = frozenset({
    "owner", "name", "descriptor", "constant_pool_index", "constant",
    "type", "bootstrap_method_attr_index",
})


def _ops(method: dict) -> list[dict[str, Any]]:
    return [
        {key: value for key, value in row.items()
         if key not in _SYMBOLIC_CP_FIELDS}
        for row in method.get("instructions", [])
    ]



def _accepted_descriptor_identity(descriptor: str, aliases: dict[str, str]) -> str | None:
    """Normalize only accepted class IDs; never wildcard unknown rs/ types.

    An unresolved class in a field descriptor has no cross-build identity
    authority even when its raw obfuscated spelling happens to be equal.
    """
    out: list[str] = []
    i = 0
    while i < len(descriptor):
        ch = descriptor[i]
        if ch != "L":
            out.append(ch)
            i += 1
            continue
        semi = descriptor.find(";", i + 1)
        _require(semi > i + 1, "INVALID_FIELD_DESCRIPTOR")
        internal = descriptor[i + 1:semi]
        if internal in aliases:
            out.append("L@" + aliases[internal] + ";")
        elif internal.startswith("rs/"):
            return None
        else:
            out.append("L" + internal + ";")
        i = semi + 1
    return "".join(out)

def _owner_accesses(method: dict, owner: str, aliases: dict[str, str]) -> list[tuple]:
    items = []
    for item in method.get("field_accesses", []):
        if item.get("owner") != owner:
            continue
        items.append((
            item["name"], item["descriptor"], item["operation"], int(item["offset"]),
            _accepted_descriptor_identity(item["descriptor"], aliases),
        ))
    return items


def build_external_field_witness_research(
    class_lineage: dict, member_lineage: dict, old_index: dict, new_index: dict,
    old_jar: Path, new_jar: Path, *, old_build_id: str, new_build_id: str,
    logical_class_id: str, min_independent_methods: int = 2,
) -> dict:
    """Compute research witnesses only. Never emit a transferable R3M proof."""
    _require(min_independent_methods >= 2, "MIN_METHODS_MUST_BE_AT_LEAST_TWO")
    _require(old_build_id != new_build_id, "BUILD_IDS_MUST_DIFFER")
    validate_lineage(class_lineage)
    validate_member_lineage(member_lineage, class_lineage=class_lineage)
    old_sha, new_sha = sha256_file(Path(old_jar)), sha256_file(Path(new_jar))
    for sha, index, build in ((old_sha, old_index, _build(class_lineage, old_build_id)),
                              (new_sha, new_index, _build(class_lineage, new_build_id))):
        _require(sha.lower() == str(index.get("sha256", "")).lower(), "JAR_INDEX_SHA_MISMATCH")
        _require(sha.lower() == str(build.get("sha256", "")).lower(), "JAR_CANONICAL_SHA_MISMATCH")
    old_classes = _class_entries(class_lineage, old_build_id)
    new_classes = _class_entries(class_lineage, new_build_id)
    _require(logical_class_id in old_classes and logical_class_id in new_classes,
             "FIELD_OWNER_NOT_CANONICAL_BOTH_BUILDS")
    old_owner, new_owner = old_classes[logical_class_id][0], new_classes[logical_class_id][0]
    old_aliases = {v[0]: k for k, v in old_classes.items()}
    new_aliases = {v[0]: k for k, v in new_classes.items()}
    candidates = _candidate_fields(
        member_lineage, old_build_id, new_build_id, logical_class_id, old_owner, new_owner
    )

    with ZipFile(old_jar) as old_archive, ZipFile(new_jar) as new_archive:
        cache: dict[tuple[str, str], dict] = {}

        def verified_profile(build_id: str, owner: str, record: dict, archive: ZipFile) -> dict:
            key = (build_id, owner)
            if key not in cache:
                entry_path = record.get("entry_path")
                _require(entry_path == owner + ".class", "CANONICAL_CLASS_ENTRY_PATH_MISMATCH")
                raw = archive.read(entry_path)
                _require(hashlib.sha256(raw).hexdigest().lower() ==
                         str(record.get("entry_sha256", "")).lower(), "ACCEPTED_CLASS_ENTRY_SHA_MISMATCH")
                p = profile_class_field_accesses(raw)
                _require(p.get("internal_name") == owner, "CLASS_HEADER_OWNER_MISMATCH")
                cache[key] = p
            return cache[key]

        old_decl = verified_profile(old_build_id, old_owner,
                                    old_classes[logical_class_id][1], old_archive)
        new_decl = verified_profile(new_build_id, new_owner,
                                    new_classes[logical_class_id][1], new_archive)

        def declared(profile: dict, name: str, desc: str, access: Any) -> bool:
            rows = [f for f in profile.get("fields", [])
                    if f.get("name") == name and f.get("descriptor") == desc]
            return len(rows) == 1 and rows[0].get("access") == access

        for c in candidates:
            _require(declared(old_decl, c["old"]["name"], c["old"]["descriptor"],
                              c["old_access"]), "OLD_FIELD_DECLARATION_MISMATCH")
            _require(declared(new_decl, c["new"]["name"], c["new"]["descriptor"],
                              c["old_access"]), "NEW_FIELD_DECLARATION_MISMATCH")

        observations: dict[tuple[str, str], list[tuple]] = defaultdict(list)
        rejected: set[str] = set()
        veto_old: set[tuple[str, str]] = set()
        method_pairs = 0
        for method_id, canonical_owner_id, left, right in _method_rows(
                member_lineage, old_build_id, new_build_id):
            _require(canonical_owner_id in old_classes and canonical_owner_id in new_classes,
                     "METHOD_OWNER_NOT_CANONICAL")
            _require(left.get("owner_internal_name") == old_classes[canonical_owner_id][0]
                     and right.get("owner_internal_name") == new_classes[canonical_owner_id][0],
                     "METHOD_CLASS_ID_OWNER_DISAGREEMENT")
            ol, nl = left["owner_internal_name"], right["owner_internal_name"]
            old_raw = old_archive.read(ol + ".class")
            new_raw = new_archive.read(nl + ".class")
            if old_owner.encode("ascii") not in old_raw and new_owner.encode("ascii") not in new_raw:
                continue
            lp = verified_profile(old_build_id, ol,
                                  old_classes[canonical_owner_id][1], old_archive)
            rp = verified_profile(new_build_id, nl,
                                  new_classes[canonical_owner_id][1], new_archive)
            lm, rm = _find_method(lp, left), _find_method(rp, right)
            la, ra = _owner_accesses(lm, old_owner, old_aliases), _owner_accesses(rm, new_owner, new_aliases)
            if not la and not ra:
                continue
            method_pairs += 1
            if _ops(lm) != _ops(rm) or len(la) != len(ra):
                rejected.add(method_id)
                veto_old.update((x[0], x[1]) for x in la)
                continue
            for ordinal, (a, b) in enumerate(zip(la, ra)):
                if a[4] is None or b[4] is None or a[2:] != b[2:]:
                    rejected.add(method_id)
                    veto_old.add((a[0], a[1]))
                    continue
                observations[(a[0], a[1])].append((
                    method_id, canonical_owner_id, a[2], a[3], ordinal, b[0], b[1]
                ))

    proofs = []
    for c in candidates:
        old_key = (c["old"]["name"], c["old"]["descriptor"])
        hits = observations.get(old_key, [])
        relevant_ids = {r[0] for r in hits}
        this_sites = {(r[0], r[2], r[3], r[4]) for r in hits}
        ambiguous = bool(this_sites) and any(
            k != old_key and {(r[0], r[2], r[3], r[4]) for r in v} == this_sites
            for k, v in observations.items()
        )
        wrong = any((r[5], r[6]) !=
                    (c["new"]["name"], c["new"]["descriptor"]) for r in hits)
        has_disputed_method = old_key in veto_old
        valid = (len(relevant_ids) >= min_independent_methods and not wrong
                 and not ambiguous and not has_disputed_method)
        proofs.append({
            "member_id": c["member_id"], "old": c["old"], "new": c["new"],
            "distinct_canonical_method_witnesses": len(relevant_ids),
            "witness_count": len(hits),
            "status": "REVIEWABLE_EXTERNAL_ANCHORS" if valid else "BLOCKED",
            "observations": [
                {"canonical_method_id": x[0], "owner_class_id": x[1],
                 "operation": x[2], "offset": x[3], "owner_field_ordinal": x[4]}
                for x in sorted(hits)
            ],
        })
    report_material = {
        "kind": "external_canonical_field_witness_research", "schema_version": 1,
        "canonical": False, "mapping_mutation": False,
        "old_sha256": old_sha, "new_sha256": new_sha, "class_id": logical_class_id,
        "minimum_independent_methods": min_independent_methods,
        "paired_methods_with_owner_field_accesses": method_pairs,
        "disputed_method_ids": sorted(rejected), "candidates": proofs,
        "accepted_identities": 0,
    }
    return {**report_material, "report_id": "EXTFIELD_" + _digest(report_material)[:24].upper()}

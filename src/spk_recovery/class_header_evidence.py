"""Research-only JVM class-header comparison for source-recovery review.

Preserves class access, superclass, direct interfaces and classfile version.
This is *not* class identity acceptance or equivalent recovered source.
"""
from __future__ import annotations

from typing import Any


class ClassHeaderError(ValueError):
    """Missing or invalid original/candidate structural evidence."""


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise ClassHeaderError(reason)


def compare_class_headers(original: dict, rebuilt: dict) -> dict[str, Any]:
    """Compare exact JVM class headers without source-code or name publication."""
    for p in (original, rebuilt):
        _require(isinstance(p, dict), "CLASS_HEADER_PROFILE_INVALID")
        _require(
            isinstance(p.get("internal_name"), str) and bool(p["internal_name"]),
            "CLASS_HEADER_OWNER_MISSING",
        )
        _require(
            type(p.get("class_access")) is int
            and 0 <= p["class_access"] <= 65535,
            "CLASS_ACCESS_INVALID_OR_MISSING",
        )
        for key in ("classfile_major", "classfile_minor"):
            _require(
                type(p.get(key)) is int and 0 <= p[key] <= 65535,
                "CLASSFILE_VERSION_INVALID_OR_MISSING",
            )
        _require(
            p.get("super_name") is None
            or (isinstance(p.get("super_name"), str) and bool(p["super_name"])),
            "CLASS_SUPERCLASS_INVALID",
        )
        _require("super_name" in p, "CLASS_SUPERCLASS_MISSING")
        ints = p.get("interfaces")
        _require(
            isinstance(ints, list)
            and all(isinstance(x, str) and bool(x) for x in ints)
            and len(ints) == len(set(ints)),
            "CLASS_INTERFACES_INVALID_OR_MISSING",
        )
    _require(
        original["internal_name"] == rebuilt["internal_name"],
        "NO_ACCEPTED_CLASS_OWNER_ALIAS",
    )
    checks = {
        "access_flags": original["class_access"] == rebuilt["class_access"],
        "direct_superclass": original["super_name"] == rebuilt["super_name"],
        "ordered_interfaces": original["interfaces"] == rebuilt["interfaces"],
        "classfile_major": original["classfile_major"] == rebuilt["classfile_major"],
        "classfile_minor": original["classfile_minor"] == rebuilt["classfile_minor"],
    }
    return {
        "schema_version": 1,
        "research_only": True,
        "canonical_identity_accepted": False,
        "source_equivalence_certified": False,
        "class_header_exact": all(checks.values()),
        "checks": checks,
        "original_interface_count": len(original["interfaces"]),
        "candidate_interface_count": len(rebuilt["interfaces"]),
        "original_superclass_present": original["super_name"] is not None,
        "candidate_superclass_present": rebuilt["super_name"] is not None,
    }

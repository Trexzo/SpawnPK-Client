"""R441 deterministic, versioned SHA256 identity of entire Java/class inventories.

A supplied reference digest is not itself a trusted baseline: the operator
must verify its origin independently. This module deliberately has no
private-source access, filesystem operations, skip flags or CLI entrypoint.
"""
from __future__ import annotations

from hashlib import sha256
import json
import re
from typing import Mapping


class Refused(RuntimeError):
    pass


def inventory_digest(items: Mapping[str, str], kind: str) -> str:
    """Hash sorted path->file SHA pairs using an OS-independent representation.

    Paths come from sha_inventory() and must be slash-separated relative
    paths. JSON escapes newlines/quotes; a version/domain prefix prevents
    an unrelated digest from being mistaken for a Java or class inventory.
    """
    if kind not in ("java", "class"):
        raise Refused("R441_UNKNOWN_INVENTORY_KIND")
    if not items or type(items) is not dict:
        raise Refused("R441_EMPTY_OR_INVALID_INVENTORY")
    for path, digest in items.items():
        if (type(path) is not str or not path or "\\" in path
                or path.startswith("/") or ".." in path.split("/")
                or "\x00" in path or path.startswith("./")):
            raise Refused("R441_INVALID_INVENTORY_RELATIVE_PATH")
        if (type(digest) is not str
                or re.fullmatch(r"[0-9a-f]{64}", digest) is None):
            raise Refused("R441_INVALID_MEMBER_SHA")
    canonical = json.dumps(
        {"format": "SpawnPK-R441-approved-inventory-v1", "kind": kind,
         "files": sorted(items.items())},
        sort_keys=True, ensure_ascii=True, separators=(",", ":"),
    ).encode("ascii")
    return sha256(canonical).hexdigest()


def require_approved_baselines(args, source: Mapping[str, str],
                               classes: Mapping[str, str]) -> None:
    """Fail closed against independently approved whole-tree SHA references."""
    specs = (
        ("approved_source_inventory_sha256", "java", source),
        ("approved_class_inventory_sha256", "class", classes),
    )
    for attribute, kind, inventory in specs:
        expected = getattr(args, attribute, None)
        if (type(expected) is not str
                or re.fullmatch(r"[0-9a-f]{64}", expected) is None):
            raise Refused("R441_APPROVED_" + kind.upper()
                          + "_INVENTORY_SHA_REQUIRED")
        if inventory_digest(inventory, kind) != expected:
            raise Refused("R441_APPROVED_" + kind.upper()
                          + "_INVENTORY_SHA_MISMATCH")

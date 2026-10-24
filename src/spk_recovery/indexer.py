from __future__ import annotations

import hashlib
import json
from pathlib import Path
import zipfile

from .classfile import ClassFormatError, parse_class


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def index_jar(path: Path) -> dict:
    path = path.resolve()
    result = {
        "schema_version": 1,
        "source_name": path.name,
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
        "entries": {},
        "classes": {},
        "summary": {},
    }
    parse_errors = {}
    with zipfile.ZipFile(path, "r") as z:
        infos = z.infolist()
        for info in infos:
            data = z.read(info.filename)
            result["entries"][info.filename] = {
                "sha256": sha256_bytes(data),
                "size": len(data),
                "crc32": f"{info.CRC:08x}",
            }
            if info.filename.endswith(".class"):
                try:
                    c = parse_class(data)
                    result["classes"][info.filename] = {
                        "internal_name": c.name,
                        "major": c.major,
                        "minor": c.minor,
                        "access": c.access,
                        "super_name": c.super_name,
                        "interfaces": c.interfaces,
                        "field_count": len(c.fields),
                        "method_count": len(c.methods),
                        "fields": c.fields,
                        "methods": c.methods,
                        "attributes": c.attributes,
                        "inner_outer_name": c.inner_outer_name,
                        "inner_simple_name": c.inner_simple_name,
                        "enclosing_class_name": c.enclosing_class_name,
                        "literal_strings": c.literal_strings,
                        "numeric_constants": c.numeric_constants,
                        "structural_sha256": c.structural_sha256(),
                    }
                except Exception as e:
                    parse_errors[info.filename] = f"{type(e).__name__}: {e}"

    classes = result["classes"]
    rs_classes = [k for k in classes if k.startswith("rs/")]
    result["summary"] = {
        "entry_count": len(result["entries"]),
        "class_count": len(classes),
        "rs_class_count": len(rs_classes),
        "class_parse_error_count": len(parse_errors),
        "class_parse_errors": parse_errors,
        "class_major_versions": sorted({classes[k]["major"] for k in classes}),
    }
    return result



def project_class_surface(index: dict, prefix: str = "rs/") -> dict:
    """Content-bound project-class census for a *fully parsed* JAR index.

    The digest is SHA-256 of sorted class-path, NUL, lowercase entry-SHA256,
    newline rows. It does not publish class bytes, strings, methods or assets.
    It is an inventory equality witness, NOT cross-version class identity.
    """
    if not isinstance(prefix, str) or not prefix.endswith("/") or not prefix:
        raise ValueError("PROJECT_SURFACE_INVALID_SCOPE")
    entries = index.get("entries")
    classes = index.get("classes")
    if not isinstance(entries, dict) or not isinstance(classes, dict):
        raise ValueError("PROJECT_SURFACE_INDEX_MISSING")
    names = sorted(
        name for name in entries
        if isinstance(name, str) and name.startswith(prefix) and name.endswith(".class")
    )
    if not names:
        raise ValueError("PROJECT_SURFACE_EMPTY")
    majors: dict[str, int] = {}
    package_counts: dict[str, int] = {}
    rows: list[bytes] = []
    for path in names:
        entry = entries[path]
        klass = classes.get(path)
        if not isinstance(entry, dict) or not isinstance(klass, dict):
            raise ValueError("PROJECT_SURFACE_UNPARSED_CLASS " + path)
        digest = entry.get("sha256")
        if (not isinstance(digest, str) or len(digest) != 64
                or any(c not in "0123456789abcdef" for c in digest)):
            raise ValueError("PROJECT_SURFACE_INVALID_CLASS_SHA " + path)
        if klass.get("internal_name") != path[:-6]:
            raise ValueError("PROJECT_SURFACE_CLASS_PATH_MISMATCH " + path)
        major = klass.get("major")
        if type(major) is not int or major < 45 or major > 100:
            raise ValueError("PROJECT_SURFACE_INVALID_CLASS_VERSION " + path)
        rows.append((path + "\0" + digest + "\n").encode("utf-8"))
        majors[str(major)] = majors.get(str(major), 0) + 1
        parts = path[len(prefix):].split("/")
        package = parts[0] if len(parts) > 1 else "[root]"
        package_counts[package] = package_counts.get(package, 0) + 1
    return {
        "scope": prefix,
        "class_count": len(names),
        "path_sha256_manifest_digest": hashlib.sha256(b"".join(rows)).hexdigest(),
        "class_major_versions": dict(sorted(majors.items(), key=lambda r: int(r[0]))),
        "package_class_counts": dict(sorted(package_counts.items())),
        "full_jvm_class_parse": True,
        "cross_build_identity_proven": False,
    }


def write_index(index: dict, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    # Preserve ordinary non-ASCII output exactly as before. Only lone
    # UTF-16 surrogate units get escaped (e.g. \\ud800) to valid JSON text.
    # No silent replacement characters or pinned digest changes elsewhere.
    out.write_text(
        json.dumps(index, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8", errors="backslashreplace",
    )

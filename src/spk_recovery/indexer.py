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


def write_index(index: dict, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(index, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")

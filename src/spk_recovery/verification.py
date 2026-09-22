from __future__ import annotations

import json
from pathlib import Path
from typing import Any
import zipfile

from .indexer import index_jar


class VerificationError(ValueError):
    pass


def _remap_descriptor(
    descriptor: str,
    class_names: dict[str, str],
) -> str:
    out: list[str] = []
    i = 0
    while i < len(descriptor):
        ch = descriptor[i]
        if ch == "L":
            semi = descriptor.find(";", i)
            if semi < 0:
                return descriptor
            internal = descriptor[i + 1 : semi]
            out.append(
                "L" + class_names.get(internal, internal) + ";"
            )
            i = semi + 1
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def _manifest_main_class(jar: Path) -> str | None:
    with zipfile.ZipFile(jar) as z:
        try:
            raw = z.read("META-INF/MANIFEST.MF").decode(
                "utf-8",
                errors="replace",
            )
        except KeyError:
            return None

    for line in raw.replace("\r\n", "\n").split("\n"):
        if line.lower().startswith("main-class:"):
            return line.split(":", 1)[1].strip().replace(".", "/")
    return None


def _service_report(jar: Path, output_index: dict[str, Any]) -> dict[str, Any]:
    descriptors: list[dict[str, Any]] = []
    missing_internal_providers: list[dict[str, str]] = []

    with zipfile.ZipFile(jar) as z:
        names = set(z.namelist())
        for name in sorted(
            n for n in names if n.startswith("META-INF/services/")
        ):
            service_dotted = name[len("META-INF/services/") :]
            service_internal = service_dotted.replace(".", "/")
            raw = z.read(name).decode("utf-8", errors="replace")
            providers: list[str] = []
            for line in raw.splitlines():
                body = line.split("#", 1)[0].strip()
                if body:
                    providers.append(body)

            descriptor = {
                "entry": name,
                "service_internal_name": service_internal,
                "providers": providers,
            }
            descriptors.append(descriptor)

            for provider in providers:
                internal = provider.replace(".", "/")
                # Only flag providers that are expected to be bundled.
                if (
                    internal.startswith("rs/")
                    or internal.startswith("recovered/")
                ) and internal + ".class" not in output_index["entries"]:
                    missing_internal_providers.append(
                        {
                            "entry": name,
                            "provider": provider,
                        }
                    )

    return {
        "descriptors": descriptors,
        "missing_internal_providers": missing_internal_providers,
    }


def verify_transformed_jar(
    source_index: dict[str, Any],
    output_jar: Path,
    *,
    class_plan: dict[str, Any] | None = None,
    member_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    output_jar = output_jar.resolve()
    if not output_jar.is_file():
        raise VerificationError(f"output JAR does not exist: {output_jar}")

    issues: list[str] = []
    out = index_jar(output_jar)

    expected_source_sha: set[str] = set()
    if class_plan is not None:
        if (
            class_plan.get("schema_version") != 1
            or class_plan.get("kind") != "remap_plan"
        ):
            raise VerificationError("unsupported class remap plan")
        expected_source_sha.add(
            str(class_plan.get("source_sha256", "")).lower()
        )
    if member_plan is not None:
        if (
            member_plan.get("schema_version") != 1
            or member_plan.get("kind") != "member_remap_plan"
        ):
            raise VerificationError("unsupported member remap plan")
        expected_source_sha.add(
            str(member_plan.get("source_sha256", "")).lower()
        )

    source_sha = str(source_index.get("sha256", "")).lower()
    if expected_source_sha and expected_source_sha != {source_sha}:
        raise VerificationError(
            "remap plan source SHA does not match supplied source index"
        )

    source_entries = source_index.get("summary", {}).get("entry_count")
    if out["summary"]["entry_count"] != source_entries:
        issues.append(
            "entry count drift: "
            f"{out['summary']['entry_count']} != {source_entries}"
        )

    if out["summary"]["class_parse_error_count"] != 0:
        issues.append(
            "output contains class parse errors: "
            f"{out['summary']['class_parse_error_count']}"
        )

    class_names: dict[str, str] = {}
    class_checks: list[dict[str, Any]] = []
    if class_plan is not None:
        for row in class_plan.get("classes", []):
            source = row["source_internal_name"]
            target = row["target_internal_name"]
            class_names[source] = target

            source_present = source + ".class" in out["entries"]
            target_present = target + ".class" in out["classes"]
            internal_ok = (
                target_present
                and out["classes"][target + ".class"]["internal_name"]
                == target
            )
            class_checks.append(
                {
                    "logical_id": row.get("logical_id"),
                    "source_internal_name": source,
                    "target_internal_name": target,
                    "source_path_absent": not source_present,
                    "target_path_present": target_present,
                    "target_internal_name_ok": internal_ok,
                }
            )
            if source != target and source_present:
                issues.append(
                    f"stale source class remains: {source}.class"
                )
            if not target_present:
                issues.append(
                    f"target class missing: {target}.class"
                )
            elif not internal_ok:
                issues.append(
                    f"target internal name mismatch: {target}"
                )

    member_checks: list[dict[str, Any]] = []
    if member_plan is not None:
        for row in member_plan.get("members", []):
            source_owner = row["owner_internal_name"]
            owner = class_names.get(source_owner, source_owner)
            cls = out["classes"].get(owner + ".class")
            if not isinstance(cls, dict):
                issues.append(
                    f"member owner class missing after remap: {owner}"
                )
                member_checks.append(
                    {
                        "member_id": row.get("member_id"),
                        "owner_internal_name": owner,
                        "target_present": False,
                        "source_signature_absent": False,
                    }
                )
                continue

            target_desc = _remap_descriptor(
                row["descriptor"],
                class_names,
            )
            collection = (
                "fields" if row["kind"] == "field" else "methods"
            )
            target_present = any(
                m.get("name") == row["target_name"]
                and m.get("descriptor") == target_desc
                for m in cls.get(collection, [])
            )
            stale_source = any(
                m.get("name") == row["source_name"]
                and m.get("descriptor") == target_desc
                for m in cls.get(collection, [])
            )
            if row["source_name"] == row["target_name"]:
                stale_source = False

            member_checks.append(
                {
                    "member_id": row.get("member_id"),
                    "kind": row["kind"],
                    "owner_internal_name": owner,
                    "source_name": row["source_name"],
                    "target_name": row["target_name"],
                    "target_descriptor": target_desc,
                    "target_present": target_present,
                    "source_signature_absent": not stale_source,
                }
            )
            if not target_present:
                issues.append(
                    "target member missing: "
                    f"{owner}.{row['target_name']}{target_desc}"
                )
            if stale_source:
                issues.append(
                    "stale source member remains: "
                    f"{owner}.{row['source_name']}{target_desc}"
                )

    main_class = _manifest_main_class(output_jar)
    main_class_present = (
        main_class is None
        or main_class + ".class" in out["classes"]
    )
    if not main_class_present:
        issues.append(
            f"manifest Main-Class does not resolve: {main_class}"
        )

    service = _service_report(output_jar, out)
    if service["missing_internal_providers"]:
        issues.append(
            "one or more bundled service providers are missing"
        )

    return {
        "schema_version": 1,
        "kind": "transformed_jar_verification",
        "source_sha256": source_sha,
        "output_sha256": out["sha256"],
        "pass": not issues,
        "issues": issues,
        "summary": {
            "source_entries": source_entries,
            "output_entries": out["summary"]["entry_count"],
            "output_classes": out["summary"]["class_count"],
            "class_parse_errors": out["summary"]["class_parse_error_count"],
            "mapped_class_checks": len(class_checks),
            "mapped_member_checks": len(member_checks),
            "service_descriptors": len(service["descriptors"]),
            "missing_internal_service_providers": len(
                service["missing_internal_providers"]
            ),
            "manifest_main_class": main_class,
            "manifest_main_class_present": main_class_present,
        },
        "class_checks": class_checks,
        "member_checks": member_checks,
        "service_report": service,
    }


def write_json(doc: dict[str, Any], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(doc, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

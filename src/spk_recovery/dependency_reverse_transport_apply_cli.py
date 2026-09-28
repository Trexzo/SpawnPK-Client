from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .dependency_reverse_transport_apply import (
    DependencyReverseTransportApplyError,
    apply_dependency_reverse_transport,
    write_dependency_reverse_transport_application,
)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="spk-dependency-reverse-transport-apply"
    )
    p.add_argument("private_reverse_plan", type=Path)
    p.add_argument("input_project_jar", type=Path)
    p.add_argument("output_project_jar", type=Path)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument(
        "--project-prefix",
        action="append",
        default=None,
    )
    p.add_argument("--java-command", default="java")
    p.add_argument("--javac-command", default="javac")
    args = p.parse_args(argv)

    try:
        report = apply_dependency_reverse_transport(
            args.private_reverse_plan,
            args.input_project_jar,
            args.output_project_jar,
            project_prefixes=tuple(
                args.project_prefix or ["rs/", "tools/"]
            ),
            java_command=args.java_command,
            javac_command=args.javac_command,
        )
        write_dependency_reverse_transport_application(
            report,
            args.out,
        )
    except (
        DependencyReverseTransportApplyError,
        OSError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    s = report["summary"]
    print("SPK_DEPENDENCY_REVERSE_TRANSPORT_APPLY_PASS")
    print(f"application_id={report['application_id']}")
    print(f"reverse_plan_id={report['reverse_plan_id']}")
    print(f"class_mapping_count={s['class_mapping_count']}")
    print(f"field_mapping_count={s['field_mapping_count']}")
    print(f"method_mapping_count={s['method_mapping_count']}")
    print(
        "project_class_identity_changed_count="
        f"{s['project_class_identity_changed_count']}"
    )
    print(
        "reference_surface_match="
        f"{s['reference_surface_match']}"
    )
    print(f"out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

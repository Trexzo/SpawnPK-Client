from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .dependency_official_derived_compile import (
    DependencyOfficialDerivedCompileError,
    compile_official_overlay_and_restore,
    write_dependency_official_derived_compile,
)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="spk-dependency-official-derived-compile"
    )
    p.add_argument("overlay_manifest", type=Path)
    p.add_argument("overlay_source_root", type=Path)
    p.add_argument("canonical_source_root", type=Path)
    p.add_argument("private_replacement_plan", type=Path)
    p.add_argument("private_reverse_plan", type=Path)
    p.add_argument("bundled_jar", type=Path)
    p.add_argument("official_artifact", type=Path, nargs="+")
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--report-out", type=Path, required=True)
    p.add_argument(
        "--project-prefix",
        action="append",
        default=None,
    )
    p.add_argument("--java-command", default="java")
    p.add_argument("--javac-command", default="javac")
    args = p.parse_args(argv)

    try:
        report = compile_official_overlay_and_restore(
            args.overlay_manifest,
            args.overlay_source_root,
            args.canonical_source_root,
            args.private_replacement_plan,
            args.private_reverse_plan,
            args.bundled_jar,
            args.official_artifact,
            args.out_dir,
            project_prefixes=tuple(
                args.project_prefix or ["rs/", "tools/"]
            ),
            java_command=args.java_command,
            javac_command=args.javac_command,
        )
        write_dependency_official_derived_compile(
            report,
            args.report_out,
        )
    except (
        DependencyOfficialDerivedCompileError,
        OSError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    s = report["summary"]
    print("SPK_DEPENDENCY_OFFICIAL_DERIVED_COMPILE_PASS")
    print(f"compile_id={report['compile_id']}")
    print(f"overlay_id={report['overlay_id']}")
    print(f"reverse_plan_id={report['reverse_plan_id']}")
    print(
        "generated_project_class_count="
        f"{s['generated_project_class_count']}"
    )
    print(
        "reverse_reference_surface_match="
        f"{s['reverse_reference_surface_match']}"
    )
    print(
        "canonical_source_modified="
        f"{s['canonical_source_modified']}"
    )
    print(
        "bundled_runtime_dependency_modified="
        f"{s['bundled_runtime_dependency_modified']}"
    )
    print(
        "restored_project_bytecode_ready_for_runtime_assembly="
        f"{s['restored_project_bytecode_ready_for_runtime_assembly']}"
    )
    print(f"report_out={args.report_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

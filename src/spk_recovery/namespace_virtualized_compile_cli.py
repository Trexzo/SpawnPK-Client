from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .namespace_virtualized_compile import (
    NamespaceVirtualizedCompileError,
    compile_with_namespace_virtualization,
)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="spk-namespace-virtualized-compile"
    )
    p.add_argument("private_alias_plan", type=Path)
    p.add_argument("source_root", type=Path)
    p.add_argument("dependency_jar", type=Path)
    p.add_argument("--out-dir", type=Path, required=True)
    p.add_argument("--javac-command", default="javac")
    p.add_argument("--release", type=int, default=9)
    p.add_argument(
        "--extra-classpath",
        action="append",
        type=Path,
        default=[],
    )
    args = p.parse_args(argv)

    try:
        plan = json.loads(
            args.private_alias_plan.read_text(encoding="utf-8")
        )
        report = compile_with_namespace_virtualization(
            plan,
            args.source_root,
            args.dependency_jar,
            args.out_dir,
            javac_command=args.javac_command,
            release=args.release,
            extra_classpath=args.extra_classpath,
        )
    except (
        NamespaceVirtualizedCompileError,
        OSError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print("SPK_NAMESPACE_VIRTUALIZED_COMPILE_PASS")
    print(f"compile_id={report['compile_id']}")
    print(
        "canonical_source_modified="
        f"{report['canonical_source_modified']}"
    )
    print(
        "source_count="
        f"{report['compiler']['source_count']}"
    )
    print(
        "restored_class_count="
        f"{report['restored_classes']['class_count']}"
    )
    print(
        "restore_replacement_count="
        f"{report['restored_classes']['restore_replacement_count']}"
    )
    print(
        "runtime_alias_dependency_allowed="
        f"{report['runtime_alias_dependency_allowed']}"
    )
    print(
        "manifest="
        + str(
            Path(args.out_dir)
            / "namespace-virtualized-compile.json"
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

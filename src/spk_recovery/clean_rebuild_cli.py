from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .clean_rebuild import (
    CleanRebuildError,
    clean_project_rebuild,
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="spk-clean-rebuild")
    p.add_argument("recovered_manifest", type=Path)
    p.add_argument("source_readiness", type=Path)
    p.add_argument("readable_manifest", type=Path)
    p.add_argument("readable_jar", type=Path)
    p.add_argument("build_authority", type=Path)
    p.add_argument("source_root", type=Path)
    p.add_argument("--javac-command", default="javac")
    p.add_argument("--java-command", default="java")
    p.add_argument(
        "--source-prefix",
        action="append",
        dest="source_prefixes",
    )
    p.add_argument(
        "--private-diagnostic-report-out",
        type=Path,
        help=(
            "write a private identifier-bearing javac classification report; "
            "never commit this artifact"
        ),
    )
    p.add_argument(
        "--namespace-alias-plan",
        type=Path,
        help=(
            "explicit private namespace alias plan enabling compile-only "
            "namespace virtualization; default clean rebuild remains legacy"
        ),
    )
    p.add_argument(
        "--auto-namespace-alias",
        action="store_true",
        help=(
            "explicitly derive a private compile-only namespace alias plan "
            "from the verified dependency capsule; mutually exclusive with "
            "--namespace-alias-plan"
        ),
    )
    p.add_argument(
        "--private-collision-plan",
        type=Path,
        help=(
            "private identifier-bearing R8S collision remap plan required "
            "when rebuilding collision-derived source; passed by path and "
            "never loaded into public CLI output"
        ),
    )
    p.add_argument(
        "--java9-macos-eawt-compile-bridge",
        action="store_true",
        help=(
            "explicitly add the v308-required Java 9 macOS eAWT public "
            "API surface to collision-derived javac only"
        ),
    )
    p.add_argument(
        "--official-first-restored",
        action="store_true",
        help=(
            "explicitly compile a dependency API source overlay against "
            "official artifacts, then restore generated project bytecode "
            "to bundled runtime identities"
        ),
    )
    p.add_argument(
        "--official-overlay-manifest",
        type=Path,
        help="R8DEP14 dependency source overlay manifest",
    )
    p.add_argument(
        "--official-overlay-source-root",
        type=Path,
        help="R8DEP14 copied overlay source root",
    )
    p.add_argument(
        "--private-dependency-replacement-plan",
        type=Path,
        help="private R8DEP11 DEPREPLACE plan",
    )
    p.add_argument(
        "--private-dependency-reverse-plan",
        type=Path,
        help="private R8DEP15 DEPREVERSE plan",
    )
    p.add_argument(
        "--official-artifact",
        action="append",
        type=Path,
        dest="official_artifacts",
        help=(
            "verified official dependency artifact; repeat for multiple "
            "compile-only artifacts"
        ),
    )
    p.add_argument("--out-dir", type=Path, required=True)
    args = p.parse_args(argv)

    try:
        report = clean_project_rebuild(
            _load(args.recovered_manifest),
            _load(args.source_readiness),
            _load(args.readable_manifest),
            args.readable_jar,
            _load(args.build_authority),
            args.source_root,
            out_dir=args.out_dir,
            javac_command=args.javac_command,
            source_prefixes=args.source_prefixes,
            private_diagnostic_report_out=(
                args.private_diagnostic_report_out
            ),
            private_namespace_alias_plan=(
                _load(args.namespace_alias_plan)
                if args.namespace_alias_plan is not None
                else None
            ),
            auto_namespace_alias=args.auto_namespace_alias,
            private_collision_plan_path=(
                args.private_collision_plan
            ),
            official_first_restored=(
                args.official_first_restored
            ),
            official_overlay_manifest_path=(
                args.official_overlay_manifest
            ),
            official_overlay_source_root=(
                args.official_overlay_source_root
            ),
            private_dependency_replacement_plan_path=(
                args.private_dependency_replacement_plan
            ),
            private_dependency_reverse_plan_path=(
                args.private_dependency_reverse_plan
            ),
            official_artifacts=args.official_artifacts,
            java9_macos_eawt_compile_bridge=(
                args.java9_macos_eawt_compile_bridge
            ),
            java_command=args.java_command,
        )
    except (
        CleanRebuildError,
        json.JSONDecodeError,
        OSError,
        ValueError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print("SPK_CLEAN_REBUILD_" + report["status"].upper())
    print(f"rebuild_id={report['rebuild_id']}")
    print(f"status={report['status']}")
    print(
        "project_source_files="
        f"{report['source_scope']['project_source_files']}"
    )
    print(
        "expected_project_classes="
        f"{report['project_classes']['expected_count']}"
    )
    print(
        "generated_project_classes="
        f"{report['project_classes']['generated_count']}"
    )
    print(
        "project_binary_fallback_count="
        f"{report['project_classes']['binary_fallback_count']}"
    )
    if report["rebuilt_client"]["sha256"]:
        print(
            "rebuilt_jar_sha256="
            f"{report['rebuilt_client']['sha256']}"
        )
    diagnostic = report["compiler"].get(
        "diagnostic_classification"
    )
    if diagnostic is not None:
        summary = diagnostic["summary"]
        cannot = summary["cannot_find_symbol"]
        print(f"javac_diagnostic_report_id={diagnostic['report_id']}")
        print(f"javac_frontier_id={diagnostic['frontier_id']}")
        print(f"javac_total_errors={summary['total_errors']}")
        print(f"javac_affected_files={summary['affected_files']}")
        print(
            "javac_categories_json="
            + json.dumps(
                summary["categories"],
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        print(f"javac_cannot_find_symbol={cannot['count']}")
        print(
            "javac_cannot_find_symbol_kinds_json="
            + json.dumps(
                cannot["symbol_kinds"],
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        print(
            "javac_cannot_find_symbol_shapes_json="
            + json.dumps(
                cannot["symbol_shapes"],
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        print(
            "javac_cannot_find_symbol_top_clusters_json="
            + json.dumps(
                cannot.get("symbol_clusters", [])[:20],
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        print(
            "javac_cannot_find_symbol_top_locations_json="
            + json.dumps(
                cannot.get("location_clusters", [])[:20],
                sort_keys=True,
                separators=(",", ":"),
            )
        )
    transport = report.get("compile_transport")
    if transport is not None:
        mode = str(transport["mode"])
        print(f"compile_transport_mode={mode}")

        if mode == "namespace_virtualized":
            print(
                "namespace_compile_id="
                f"{transport['namespace_compile_id']}"
            )
            print(
                "namespace_alias_plan_id="
                f"{transport['alias_plan_id']}"
            )
            print(
                "namespace_alias_plan_source="
                f"{transport['alias_plan_source']}"
            )
            print(
                "runtime_alias_dependency_allowed="
                f"{transport['runtime_alias_dependency_allowed']}"
            )
        elif mode == "official_first_restored":
            print(
                "official_compile_id="
                f"{transport['official_compile_id']}"
            )
            print(
                "dependency_overlay_id="
                f"{transport['overlay_id']}"
            )
            print(
                "dependency_replacement_plan_id="
                f"{transport['replacement_plan_id']}"
            )
            print(
                "dependency_reverse_plan_id="
                f"{transport['reverse_plan_id']}"
            )
            print(
                "runtime_official_dependencies_allowed="
                f"{transport['runtime_official_dependencies_allowed']}"
            )
            print(
                "restored_project_bytecode_ready_for_runtime_assembly="
                f"{transport['restored_project_bytecode_ready_for_runtime_assembly']}"
            )
        elif mode == "collision_derived_remap":
            bridges = transport.get(
                "compile_only_platform_bridges",
                [],
            )
            if bridges:
                print(
                    "compile_only_platform_bridge_ids_json="
                    + json.dumps(
                        [
                            row["bridge_id"]
                            for row in bridges
                        ],
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                )
            print(
                "runtime_platform_bridges_allowed="
                f"{transport.get('runtime_platform_bridges_allowed', False)}"
            )
            print(
                "collision_compile_id="
                f"{transport['collision_compile_id']}"
            )
            print(
                "collision_transform_id="
                f"{transport['collision_transform_id']}"
            )
            print(
                "collision_plan_id="
                f"{transport['collision_plan_id']}"
            )
            print(
                "collision_report_id="
                f"{transport['collision_report_id']}"
            )
            print(
                "runtime_transformed_dependency_allowed="
                f"{transport['runtime_transformed_dependency_allowed']}"
            )
        else:
            raise ValueError(
                "unsupported compile transport mode: " + mode
            )


    if args.private_diagnostic_report_out is not None:
        print(
            "private_diagnostic_report_out="
            f"{args.private_diagnostic_report_out.resolve()}"
        )
    print(f"out_dir={args.out_dir.resolve()}")
    return 0 if report["status"] == "complete" else 3


if __name__ == "__main__":
    raise SystemExit(main())

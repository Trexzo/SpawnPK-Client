from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .source_authority_artifact import (
    SourceAuthorityArtifactError,
    build_source_authority_artifact,
    load_authority_artifact_inputs,
    verify_source_authority_artifact,
)


def _reject_output_inside_artifact(
    out: Path,
    artifact_dir: Path,
) -> None:
    resolved_out = out.resolve()
    resolved_artifact = artifact_dir.resolve()
    try:
        resolved_out.relative_to(resolved_artifact)
    except ValueError:
        return
    raise SourceAuthorityArtifactError(
        "verification output must be outside authority artifact"
    )


def _write_json(doc: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        (
            json.dumps(
                doc,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="spk-source-authority-artifact"
    )
    sub = parser.add_subparsers(
        dest="command",
        required=True,
    )

    build = sub.add_parser("build")
    build.add_argument("--authority-commit", required=True)
    build.add_argument(
        "--class-lineage",
        type=Path,
        required=True,
    )
    build.add_argument(
        "--member-lineage",
        type=Path,
        required=True,
    )
    build.add_argument(
        "--semantic-review",
        type=Path,
        required=True,
    )
    build.add_argument(
        "--semantic-acceptance",
        type=Path,
        required=True,
    )
    build.add_argument(
        "--readable-manifest",
        type=Path,
        required=True,
    )
    build.add_argument(
        "--recovered-manifest",
        type=Path,
        required=True,
    )
    build.add_argument(
        "--clean-rebuild",
        type=Path,
        required=True,
    )
    build.add_argument(
        "--release-manifest",
        type=Path,
        required=True,
    )
    build.add_argument(
        "--release-verification",
        type=Path,
        required=True,
    )
    build.add_argument(
        "--source-root",
        type=Path,
        required=True,
    )
    build.add_argument(
        "--authority-repository",
        default="Trexzo/SpawnPK-Client",
    )
    build.add_argument(
        "--publication-repository",
        default="Trexzo/SpawnPK-Client-Source",
    )
    build.add_argument(
        "--out-dir",
        type=Path,
        required=True,
    )

    verify = sub.add_parser("verify")
    verify.add_argument(
        "--artifact-dir",
        type=Path,
        required=True,
    )
    verify.add_argument(
        "--expected-authority-commit",
        required=True,
    )
    verify.add_argument(
        "--expected-milestone-id",
        required=True,
    )
    verify.add_argument(
        "--out",
        type=Path,
        required=True,
    )

    args = parser.parse_args(argv)

    try:
        if args.command == "build":
            inputs = load_authority_artifact_inputs(
                class_lineage=args.class_lineage,
                member_lineage=args.member_lineage,
                semantic_review=args.semantic_review,
                semantic_acceptance=args.semantic_acceptance,
                readable_manifest=args.readable_manifest,
                recovered_manifest=args.recovered_manifest,
                clean_rebuild=args.clean_rebuild,
                release_manifest=args.release_manifest,
                release_verification=args.release_verification,
            )
            report = build_source_authority_artifact(
                authority_commit=args.authority_commit,
                source_root=args.source_root,
                out_dir=args.out_dir,
                authority_repository=(
                    args.authority_repository
                ),
                publication_repository=(
                    args.publication_repository
                ),
                **inputs,
            )
            print(
                "SPK_SOURCE_AUTHORITY_ARTIFACT_BUILD_COMPLETE"
            )
            print(f"artifact_id={report['artifact_id']}")
            print(
                "preflight_milestone_id="
                + report["preflight_milestone_id"]
            )
            print(
                "source_tree_sha256="
                + report["source_tree_sha256"]
            )
            print(
                "source_file_count="
                + str(report["source_file_count"])
            )
            print(f"out_dir={args.out_dir}")
            return 0

        _reject_output_inside_artifact(
            args.out,
            args.artifact_dir,
        )
        report = verify_source_authority_artifact(
            args.artifact_dir,
            expected_authority_commit=(
                args.expected_authority_commit
            ),
            expected_milestone_id=args.expected_milestone_id,
        )
        _write_json(report, args.out)
        print(
            "SPK_SOURCE_AUTHORITY_ARTIFACT_VERIFY_COMPLETE"
        )
        print(
            f"verification_id={report['verification_id']}"
        )
        print(
            "verified="
            + str(report["verified"]).lower()
        )
        print(
            "source_tree_sha256="
            + report["source_tree_sha256"]
        )
        print(
            "payload_file_count="
            + str(report["payload_file_count"])
        )
        print(f"out={args.out}")
        return 0 if report["verified"] else 3
    except (
        SourceAuthorityArtifactError,
        OSError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .lineage import load_lineage
from .member_lineage import load_member_lineage
from .source_milestone import (
    SourceMilestoneError,
    build_source_milestone_manifest,
    build_source_publication_bundle,
    stage_source_publication_bundle,
    verify_source_milestone_manifest,
    verify_source_publication_bundle,
    write_json,
)


def _exact_object(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise SourceMilestoneError(
                f"duplicate JSON key: {key!r}"
            )
        out[key] = value
    return out


def _load(path: Path) -> dict:
    value = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_exact_object,
    )
    if not isinstance(value, dict):
        raise SourceMilestoneError(
            f"expected JSON object: {path}"
        )
    return value


def _reject_output_overlap(
    out: Path,
    *,
    authority_roots: tuple[Path, ...] = (),
    input_files: tuple[Path, ...] = (),
) -> None:
    resolved_out = out.resolve()
    for root in authority_roots:
        resolved_root = root.resolve()
        try:
            resolved_out.relative_to(resolved_root)
        except ValueError:
            pass
        else:
            raise SourceMilestoneError(
                "output path must be outside authority tree: "
                + str(root)
            )
    for input_path in input_files:
        if resolved_out == input_path.resolve():
            raise SourceMilestoneError(
                "output path must not overwrite input authority: "
                + str(input_path)
            )


def _common_input_paths(args: argparse.Namespace) -> tuple[Path, ...]:
    return (
        args.class_lineage,
        args.member_lineage,
        args.semantic_review,
        args.semantic_acceptance,
        args.readable_manifest,
        args.recovered_manifest,
        args.clean_rebuild,
        args.release_manifest,
        args.release_verification,
    )


def _common_inputs(p: argparse.ArgumentParser) -> None:
    p.add_argument("--authority-commit", required=True)
    p.add_argument("--class-lineage", type=Path, required=True)
    p.add_argument("--member-lineage", type=Path, required=True)
    p.add_argument("--semantic-review", type=Path, required=True)
    p.add_argument("--semantic-acceptance", type=Path, required=True)
    p.add_argument("--readable-manifest", type=Path, required=True)
    p.add_argument("--recovered-manifest", type=Path, required=True)
    p.add_argument("--clean-rebuild", type=Path, required=True)
    p.add_argument("--release-manifest", type=Path, required=True)
    p.add_argument("--release-verification", type=Path, required=True)
    p.add_argument("--source-root", type=Path, required=True)
    p.add_argument(
        "--authority-repository",
        default="Trexzo/SpawnPK-Client",
    )
    p.add_argument(
        "--publication-repository",
        default="Trexzo/SpawnPK-Client",
    )
    p.add_argument(
        "--publication-root",
        default="recovered-source/v308/",
    )


def _kwargs(args: argparse.Namespace) -> dict:
    # Reject duplicate JSON keys here. Full class/member lineage schema and
    # cross-link validation is enforced by the final Source-Milestone builder.
    _load(args.class_lineage)
    _load(args.member_lineage)
    return {
        "authority_commit": args.authority_commit,
        "class_lineage": load_lineage(args.class_lineage),
        "member_lineage": load_member_lineage(
            args.member_lineage
        ),
        "semantic_review": _load(args.semantic_review),
        "semantic_acceptance": _load(args.semantic_acceptance),
        "readable_manifest": _load(args.readable_manifest),
        "recovered_source_manifest": _load(
            args.recovered_manifest
        ),
        "clean_rebuild_report": _load(args.clean_rebuild),
        "release_manifest": _load(args.release_manifest),
        "release_verification": _load(
            args.release_verification
        ),
        "source_root": args.source_root,
        "authority_repository": args.authority_repository,
        "publication_repository": args.publication_repository,
        "publication_root": args.publication_root,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="spk-source-milestone")
    sub = p.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build")
    _common_inputs(build)
    build.add_argument("--out", type=Path, required=True)

    verify = sub.add_parser("verify")
    _common_inputs(verify)
    verify.add_argument("--manifest", type=Path, required=True)
    verify.add_argument("--out", type=Path, required=True)

    verify_bundle = sub.add_parser("verify-bundle")
    verify_bundle.add_argument(
        "--bundle-dir",
        type=Path,
        required=True,
    )
    verify_bundle.add_argument(
        "--manifest",
        type=Path,
        required=True,
    )
    verify_bundle.add_argument(
        "--expected-authority-commit",
        required=True,
    )
    verify_bundle.add_argument(
        "--out",
        type=Path,
        required=True,
    )

    bundle = sub.add_parser("bundle")
    bundle.add_argument("--manifest", type=Path, required=True)
    bundle.add_argument("--source-root", type=Path, required=True)
    bundle.add_argument("--out-dir", type=Path, required=True)
    bundle.add_argument(
        "--provenance",
        action="append",
        default=[],
        metavar="NAME=PATH",
    )

    stage = sub.add_parser("stage-repository")
    stage.add_argument("--bundle-dir", type=Path, required=True)
    stage.add_argument("--manifest", type=Path, required=True)
    stage.add_argument("--expected-authority-commit", required=True)
    stage.add_argument("--repository-root", type=Path, required=True)

    args = p.parse_args(argv)

    try:
        if args.command == "build":
            _reject_output_overlap(
                args.out,
                authority_roots=(args.source_root,),
                input_files=_common_input_paths(args),
            )
            manifest = build_source_milestone_manifest(
                **_kwargs(args)
            )
            write_json(manifest, args.out)
            print("SPK_SOURCE_MILESTONE_BUILD_COMPLETE")
            print(f"milestone_id={manifest['milestone_id']}")
            print(
                "publishable="
                + str(manifest["publishable"]).lower()
            )
            print(
                "blocker_count="
                + str(len(manifest["blockers"]))
            )
            print(f"out={args.out}")
            return 0 if manifest["publishable"] else 3

        if args.command == "verify":
            _reject_output_overlap(
                args.out,
                authority_roots=(args.source_root,),
                input_files=(
                    *_common_input_paths(args),
                    args.manifest,
                ),
            )
            manifest = _load(args.manifest)
            report = verify_source_milestone_manifest(
                manifest,
                **_kwargs(args),
            )
            write_json(report, args.out)
            print("SPK_SOURCE_MILESTONE_VERIFY_COMPLETE")
            print(
                f"verification_id={report['verification_id']}"
            )
            print(
                "verified="
                + str(report["verified"]).lower()
            )
            print(
                "publishable="
                + str(report["publishable"]).lower()
            )
            print(f"out={args.out}")
            return 0 if report["verified"] else 3

        if args.command == "verify-bundle":
            _reject_output_overlap(
                args.out,
                authority_roots=(args.bundle_dir,),
                input_files=(args.manifest,),
            )
            expected_manifest = _load(args.manifest)
            report = verify_source_publication_bundle(
                args.bundle_dir,
                expected_manifest=expected_manifest,
                expected_authority_commit=(
                    args.expected_authority_commit
                ),
            )
            write_json(report, args.out)
            print(
                "SPK_SOURCE_MILESTONE_BUNDLE_VERIFY_COMPLETE"
            )
            print(
                f"verification_id={report['verification_id']}"
            )
            print(
                "verified="
                + str(report["verified"]).lower()
            )
            print(
                "indexed_file_count="
                + str(report["indexed_file_count"])
            )
            print(
                "provenance_document_count="
                + str(report["provenance_document_count"])
            )
            print(f"out={args.out}")
            return 0 if report["verified"] else 3

        if args.command == "stage-repository":
            manifest = _load(args.manifest)
            staged = stage_source_publication_bundle(
                args.bundle_dir,
                args.repository_root,
                expected_manifest=manifest,
                expected_authority_commit=(
                    args.expected_authority_commit
                ),
            )
            print("SPK_SOURCE_MILESTONE_REPOSITORY_STAGE_COMPLETE")
            print(f"milestone_id={staged['milestone_id']}")
            print(
                "bundle_verification_id="
                + str(staged["bundle_verification_id"])
            )
            print(
                "staged_bundle_verification_id="
                + str(staged["staged_bundle_verification_id"])
            )
            print(f"repository_root={staged['repository_root']}")
            print(f"file_count={staged['file_count']}")
            print(f"target_path={staged['target_path']}")
            return 0

        provenance: dict[str, dict] = {}
        for item in args.provenance:
            if "=" not in item:
                raise SourceMilestoneError(
                    "--provenance requires NAME=PATH"
                )
            name, raw_path = item.split("=", 1)
            provenance[name] = _load(Path(raw_path))

        manifest = _load(args.manifest)
        bundle_report = build_source_publication_bundle(
            manifest,
            args.source_root,
            args.out_dir,
            provenance_documents=provenance,
        )
        print("SPK_SOURCE_MILESTONE_BUNDLE_COMPLETE")
        print(f"bundle_id={bundle_report['bundle_id']}")
        print(
            "source_file_count="
            + str(bundle_report["source_file_count"])
        )
        print(f"out_dir={args.out_dir}")
        return 0
    except (
        SourceMilestoneError,
        OSError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

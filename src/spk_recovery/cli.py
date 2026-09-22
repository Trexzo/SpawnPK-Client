from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .indexer import index_jar, write_index
from .diffing import diff_indexes
from .decompiler import (
    DecompilerError,
    run_decompiler,
    write_json as write_decompiler_json,
)
from .verification import (
    VerificationError,
    verify_transformed_jar,
    write_json as write_verify_json,
)
from .canonicalize import CandidateApplicationError, apply_lineage_candidates
from .promotion import NewClassPromotionError, promote_new_classes
from .repack import RepackError, remap_jar, write_result
from .remap_plan import (
    RemapPlanError,
    build_remap_plan,
    remap_risk_scan,
    write_json,
)
from .semantic_review import (
    SemanticReviewError,
    accept_semantic_proposals,
    resolve_semantic_candidates,
    write_json as write_semantic_json,
)
from .member_safety import (
    MemberSafetyError,
    build_member_safety_report,
    validate_member_safety_acceptance,
    write_json as write_member_safety_json,
)
from .member_remap_plan import (
    MemberRemapPlanError,
    build_member_remap_plan,
    write_json as write_member_remap_json,
)
from .member_lineage import (
    MemberLineageError,
    load_member_lineage,
    seed_member_lineage,
    validate_member_lineage,
    write_member_lineage,
)
from .lineage import (
    LineageValidationError,
    load_lineage,
    seed_lineage,
    validate_lineage,
    write_lineage,
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="spk-recovery")
    sub = p.add_subparsers(dest="cmd", required=True)

    pi = sub.add_parser(
        "index",
        help="Index and fingerprint a client JAR",
    )
    pi.add_argument("jar", type=Path)
    pi.add_argument("--out", type=Path, required=True)
    pi.add_argument("--expect-sha256")

    pd = sub.add_parser(
        "diff",
        help="Compare two previously generated indexes",
    )
    pd.add_argument("old", type=Path)
    pd.add_argument("new", type=Path)
    pd.add_argument("--out", type=Path, required=True)

    ps = sub.add_parser(
        "lineage-seed",
        help="Create deterministic logical class IDs from an exact baseline index",
    )
    ps.add_argument("index", type=Path)
    ps.add_argument("--build-id", required=True)
    ps.add_argument("--build-number", type=int)
    ps.add_argument("--authority", default="EXACT_CURRENT_CLIENT")
    ps.add_argument("--prefix", default="rs/")
    ps.add_argument("--out", type=Path, required=True)

    pv = sub.add_parser(
        "lineage-validate",
        help="Validate a canonical logical-lineage document",
    )
    pv.add_argument("lineage", type=Path)

    pms = sub.add_parser(
        "member-lineage-seed",
        help="Create deterministic field/method IDs from an exact class-lineage baseline",
    )
    pms.add_argument("class_lineage", type=Path)
    pms.add_argument("index", type=Path)
    pms.add_argument("--build-id", required=True)
    pms.add_argument("--out", type=Path, required=True)

    pmv = sub.add_parser(
        "member-lineage-validate",
        help="Validate a canonical member-lineage document",
    )
    pmv.add_argument("member_lineage", type=Path)
    pmv.add_argument("--class-lineage", type=Path)

    psr = sub.add_parser(
        "semantic-resolve",
        help="Resolve non-canonical semantic candidates to stable class/member IDs",
    )
    psr.add_argument("class_lineage", type=Path)
    psr.add_argument("member_lineage", type=Path)
    psr.add_argument("candidates", type=Path)
    psr.add_argument("--out", type=Path, required=True)

    psa = sub.add_parser(
        "semantic-accept",
        help="Explicitly accept reviewed semantic proposal IDs into canonical lineage",
    )
    psa.add_argument("class_lineage", type=Path)
    psa.add_argument("member_lineage", type=Path)
    psa.add_argument("review", type=Path)
    psa.add_argument("acceptance", type=Path)
    psa.add_argument("--class-out", type=Path, required=True)
    psa.add_argument("--member-out", type=Path, required=True)

    pa = sub.add_parser(
        "lineage-apply-candidates",
        help="Verify and apply matcher candidates to canonical lineage",
    )
    pa.add_argument("lineage", type=Path)
    pa.add_argument("old_index", type=Path)
    pa.add_argument("new_index", type=Path)
    pa.add_argument("candidates", type=Path)
    pa.add_argument("--old-build-id", required=True)
    pa.add_argument("--new-build-id", required=True)
    pa.add_argument("--new-build-number", type=int)
    pa.add_argument("--new-authority", default="CROSS_BUILD")
    pa.add_argument("--minimum-weighted-score", type=float, default=0.88)
    pa.add_argument("--out", type=Path, required=True)

    pp = sub.add_parser(
        "lineage-promote-new",
        help="Explicitly promote reviewed unmatched-new classes into logical IDs",
    )
    pp.add_argument("lineage", type=Path)
    pp.add_argument("new_index", type=Path)
    pp.add_argument("--build-id", required=True)
    pp.add_argument(
        "--path",
        action="append",
        dest="paths",
        required=True,
    )
    pp.add_argument("--authority", default="RESEARCH")
    pp.add_argument(
        "--note",
        default="Explicitly reviewed and promoted from unmatched_new.",
    )
    pp.add_argument("--out", type=Path, required=True)

    rp = sub.add_parser(
        "remap-plan",
        help="Resolve an explicit logical-ID remap spec for one exact client build",
    )
    rp.add_argument("lineage", type=Path)
    rp.add_argument("spec", type=Path)
    rp.add_argument("--out", type=Path, required=True)

    rr = sub.add_parser(
        "remap-risk-scan",
        help="Scan a resolved remap plan for reflection/resource/repackage risks",
    )
    rr.add_argument("index", type=Path)
    rr.add_argument("plan", type=Path)
    rr.add_argument("--out", type=Path, required=True)

    pmrp = sub.add_parser(
        "member-remap-plan",
        help="Build an exact-build member remap plan from ACCEPTED semantic names",
    )
    pmrp.add_argument("class_lineage", type=Path)
    pmrp.add_argument("member_lineage", type=Path)
    pmrp.add_argument("index", type=Path)
    pmrp.add_argument("--build-id", required=True)
    pmrp.add_argument("--out", type=Path, required=True)

    pmsr = sub.add_parser(
        "member-safety-scan",
        help="Build exact per-member name-sensitivity risk evidence",
    )
    pmsr.add_argument("source_jar", type=Path)
    pmsr.add_argument("index", type=Path)
    pmsr.add_argument("member_plan", type=Path)
    pmsr.add_argument("--out", type=Path, required=True)

    pmsv = sub.add_parser(
        "member-safety-validate",
        help="Validate explicit acceptance against one exact member safety report",
    )
    pmsv.add_argument("member_plan", type=Path)
    pmsv.add_argument("report", type=Path)
    pmsv.add_argument("acceptance", type=Path)

    rc = sub.add_parser(
        "class-remap",
        help="Apply a verified class remap plan and deterministically repackage the JAR",
    )
    rc.add_argument("source_jar", type=Path)
    rc.add_argument("index", type=Path)
    rc.add_argument("plan", type=Path)
    rc.add_argument("--out", type=Path, required=True)
    rc.add_argument("--result-out", type=Path)
    rc.add_argument("--rewrite-class-name-strings", action="store_true")
    rc.add_argument("--allow-package-resource-risk", action="store_true")

    rj = sub.add_parser(
        "jar-remap",
        help="Apply verified class and/or member remap plans to one exact client JAR",
    )
    rj.add_argument("source_jar", type=Path)
    rj.add_argument("index", type=Path)
    rj.add_argument("--class-plan", type=Path)
    rj.add_argument("--member-plan", type=Path)
    rj.add_argument("--out", type=Path, required=True)
    rj.add_argument("--result-out", type=Path)
    rj.add_argument("--rewrite-class-name-strings", action="store_true")
    rj.add_argument("--allow-package-resource-risk", action="store_true")
    rj.add_argument("--allow-member-reflection-risk", action="store_true")
    rj.add_argument("--member-safety-report", type=Path)
    rj.add_argument("--member-safety-acceptance", type=Path)

    rv = sub.add_parser(
        "verify-remap",
        help="Independently verify a transformed client JAR against exact remap plans",
    )
    rv.add_argument("source_index", type=Path)
    rv.add_argument("output_jar", type=Path)
    rv.add_argument("--class-plan", type=Path)
    rv.add_argument("--member-plan", type=Path)
    rv.add_argument("--out", type=Path, required=True)

    rd = sub.add_parser(
        "decompile",
        help="Run a hash-pinned CFR or Vineflower JAR against a transformed client",
    )
    rd.add_argument("input_jar", type=Path)
    rd.add_argument("decompiler_jar", type=Path)
    rd.add_argument("--decompiler-sha256", required=True)
    rd.add_argument("--engine", choices=["cfr", "vineflower"], required=True)
    rd.add_argument("--out-dir", type=Path, required=True)
    rd.add_argument("--clean-out", action="store_true")
    rd.add_argument("--result-out", type=Path)

    args = p.parse_args(argv)
    if args.cmd == "index":
        idx = index_jar(args.jar)
        if (
            args.expect_sha256
            and idx["sha256"].lower() != args.expect_sha256.lower()
        ):
            print(
                f"REFUSED: SHA-256 {idx['sha256']} != expected "
                f"{args.expect_sha256}",
                file=sys.stderr,
            )
            return 2
        write_index(idx, args.out)
        print("SPK_RECOVERY_INDEX_PASS")
        print(f"sha256={idx['sha256']}")
        print(f"entries={idx['summary']['entry_count']}")
        print(f"classes={idx['summary']['class_count']}")
        print(f"rs_classes={idx['summary']['rs_class_count']}")
        print(f"parse_errors={idx['summary']['class_parse_error_count']}")
        print(f"out={args.out}")
        return 0

    if args.cmd == "diff":
        report = diff_indexes(
            _load(args.old),
            _load(args.new),
        )
        args.out.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        args.out.write_text(
            json.dumps(
                report,
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        print("SPK_RECOVERY_DIFF_PASS")
        for k, v in report["summary"].items():
            print(f"{k}={v}")
        print(f"out={args.out}")
        return 0

    if args.cmd == "lineage-seed":
        try:
            doc = seed_lineage(
                _load(args.index),
                build_id=args.build_id,
                build_number=args.build_number,
                authority=args.authority,
                prefix=args.prefix,
            )
            write_lineage(
                doc,
                args.out,
            )
        except LineageValidationError as e:
            print(
                f"REFUSED: {e}",
                file=sys.stderr,
            )
            return 2
        print("SPK_RECOVERY_LINEAGE_SEED_PASS")
        print(f"build_id={args.build_id}")
        print(f"logical_classes={len(doc['classes'])}")
        print(f"out={args.out}")
        return 0

    if args.cmd == "lineage-validate":
        try:
            summary = validate_lineage(
                load_lineage(args.lineage)
            )
        except (
            LineageValidationError,
            json.JSONDecodeError,
        ) as e:
            print(
                f"REFUSED: {e}",
                file=sys.stderr,
            )
            return 2
        print("SPK_RECOVERY_LINEAGE_VALIDATE_PASS")
        for k, v in summary.items():
            print(f"{k}={v}")
        return 0

    if args.cmd == "member-lineage-seed":
        try:
            class_lineage = load_lineage(args.class_lineage)
            doc = seed_member_lineage(
                class_lineage,
                _load(args.index),
                build_id=args.build_id,
            )
            write_member_lineage(doc, args.out)
        except (
            MemberLineageError,
            LineageValidationError,
            json.JSONDecodeError,
        ) as e:
            print(f"REFUSED: {e}", file=sys.stderr)
            return 2
        summary = validate_member_lineage(
            doc,
            class_lineage=class_lineage,
        )
        print("SPK_RECOVERY_MEMBER_LINEAGE_SEED_PASS")
        for k, v in summary.items():
            print(f"{k}={v}")
        print(f"out={args.out}")
        return 0

    if args.cmd == "member-lineage-validate":
        try:
            member_doc = load_member_lineage(args.member_lineage)
            class_doc = (
                load_lineage(args.class_lineage)
                if args.class_lineage
                else None
            )
            summary = validate_member_lineage(
                member_doc,
                class_lineage=class_doc,
            )
        except (
            MemberLineageError,
            LineageValidationError,
            json.JSONDecodeError,
        ) as e:
            print(f"REFUSED: {e}", file=sys.stderr)
            return 2
        print("SPK_RECOVERY_MEMBER_LINEAGE_VALIDATE_PASS")
        for k, v in summary.items():
            print(f"{k}={v}")
        return 0

    if args.cmd == "semantic-resolve":
        try:
            review = resolve_semantic_candidates(
                load_lineage(args.class_lineage),
                load_member_lineage(args.member_lineage),
                _load(args.candidates),
            )
            write_semantic_json(review, args.out)
        except (
            SemanticReviewError,
            LineageValidationError,
            MemberLineageError,
            json.JSONDecodeError,
        ) as e:
            print(f"REFUSED: {e}", file=sys.stderr)
            return 2
        print("SPK_RECOVERY_SEMANTIC_RESOLVE_PASS")
        print(f"review_id={review['review_id']}")
        print(f"proposals={review['proposal_count']}")
        print(f"unresolved={len(review['unresolved'])}")
        print(f"out={args.out}")
        return 0

    if args.cmd == "semantic-accept":
        try:
            out_classes, out_members, summary = accept_semantic_proposals(
                load_lineage(args.class_lineage),
                load_member_lineage(args.member_lineage),
                _load(args.review),
                _load(args.acceptance),
            )
            write_lineage(out_classes, args.class_out)
            write_member_lineage(out_members, args.member_out)
        except (
            SemanticReviewError,
            LineageValidationError,
            MemberLineageError,
            json.JSONDecodeError,
        ) as e:
            print(f"REFUSED: {e}", file=sys.stderr)
            return 2
        print("SPK_RECOVERY_SEMANTIC_ACCEPT_PASS")
        for k, v in summary.items():
            print(f"{k}={v}")
        print(f"class_out={args.class_out}")
        print(f"member_out={args.member_out}")
        return 0

    if args.cmd == "lineage-apply-candidates":
        try:
            out, summary = apply_lineage_candidates(
                load_lineage(args.lineage),
                _load(args.old_index),
                _load(args.new_index),
                _load(args.candidates),
                old_build_id=args.old_build_id,
                new_build_id=args.new_build_id,
                new_build_number=args.new_build_number,
                new_authority=args.new_authority,
                minimum_weighted_score=(
                    args.minimum_weighted_score
                ),
            )
            write_lineage(
                out,
                args.out,
            )
        except (
            CandidateApplicationError,
            LineageValidationError,
            json.JSONDecodeError,
        ) as e:
            print(
                f"REFUSED: {e}",
                file=sys.stderr,
            )
            return 2
        print("SPK_RECOVERY_LINEAGE_APPLY_PASS")
        for k, v in summary.items():
            print(f"{k}={v}")
        print(f"out={args.out}")
        return 0

    if args.cmd == "lineage-promote-new":
        try:
            out, summary = promote_new_classes(
                load_lineage(args.lineage),
                _load(args.new_index),
                build_id=args.build_id,
                paths=args.paths,
                authority=args.authority,
                note=args.note,
            )
            write_lineage(
                out,
                args.out,
            )
        except (
            NewClassPromotionError,
            LineageValidationError,
            json.JSONDecodeError,
        ) as e:
            print(
                f"REFUSED: {e}",
                file=sys.stderr,
            )
            return 2
        print("SPK_RECOVERY_LINEAGE_PROMOTE_NEW_PASS")
        for k, v in summary.items():
            print(f"{k}={v}")
        print(f"out={args.out}")
        return 0

    if args.cmd == "remap-plan":
        try:
            plan = build_remap_plan(
                load_lineage(args.lineage),
                _load(args.spec),
            )
            write_json(
                plan,
                args.out,
            )
        except (
            RemapPlanError,
            LineageValidationError,
            json.JSONDecodeError,
        ) as e:
            print(
                f"REFUSED: {e}",
                file=sys.stderr,
            )
            return 2
        print("SPK_RECOVERY_REMAP_PLAN_PASS")
        print(f"build_id={plan['build_id']}")
        print(f"mapped_classes={plan['class_count']}")
        print(f"out={args.out}")
        return 0

    if args.cmd == "remap-risk-scan":
        try:
            report = remap_risk_scan(
                _load(args.index),
                _load(args.plan),
            )
            write_json(
                report,
                args.out,
            )
        except (
            RemapPlanError,
            json.JSONDecodeError,
        ) as e:
            print(
                f"REFUSED: {e}",
                file=sys.stderr,
            )
            return 2
        print("SPK_RECOVERY_REMAP_RISK_SCAN_PASS")
        for k, v in report["summary"].items():
            print(f"{k}={v}")
        print(f"out={args.out}")
        return 0

    if args.cmd == "member-remap-plan":
        try:
            plan = build_member_remap_plan(
                load_lineage(args.class_lineage),
                load_member_lineage(args.member_lineage),
                _load(args.index),
                build_id=args.build_id,
            )
            write_member_remap_json(plan, args.out)
        except (
            MemberRemapPlanError,
            MemberLineageError,
            LineageValidationError,
            json.JSONDecodeError,
        ) as e:
            print(f"REFUSED: {e}", file=sys.stderr)
            return 2
        print("SPK_RECOVERY_MEMBER_REMAP_PLAN_PASS")
        print(f"mapped_members={plan['member_count']}")
        print(f"mapped_fields={plan['field_count']}")
        print(f"mapped_methods={plan['method_count']}")
        print(f"out={args.out}")
        return 0

    if args.cmd == "member-safety-scan":
        try:
            report = build_member_safety_report(
                args.source_jar,
                _load(args.index),
                _load(args.member_plan),
            )
            write_member_safety_json(report, args.out)
        except (
            MemberSafetyError,
            json.JSONDecodeError,
        ) as e:
            print(f"REFUSED: {e}", file=sys.stderr)
            return 2
        print("SPK_RECOVERY_MEMBER_SAFETY_SCAN_PASS")
        print(f"report_id={report['report_id']}")
        print(f"member_count={report['member_count']}")
        for level, count in report["risk_level_counts"].items():
            print(f"risk_{level}={count}")
        print(f"out={args.out}")
        return 0

    if args.cmd == "member-safety-validate":
        try:
            summary = validate_member_safety_acceptance(
                _load(args.member_plan),
                _load(args.report),
                _load(args.acceptance),
            )
        except (
            MemberSafetyError,
            json.JSONDecodeError,
        ) as e:
            print(f"REFUSED: {e}", file=sys.stderr)
            return 2
        print("SPK_RECOVERY_MEMBER_SAFETY_VALIDATE_PASS")
        for k, v in summary.items():
            print(f"{k}={v}")
        return 0

    if args.cmd == "class-remap":
        try:
            result = remap_jar(
                args.source_jar,
                _load(args.index),
                _load(args.plan),
                args.out,
                allow_package_resource_risk=(
                    args.allow_package_resource_risk
                ),
                rewrite_class_name_strings=(
                    args.rewrite_class_name_strings
                ),
            )
            if args.result_out:
                write_result(result, args.result_out)
        except (
            RepackError,
            json.JSONDecodeError,
        ) as e:
            print(
                f"REFUSED: {e}",
                file=sys.stderr,
            )
            return 2
        print("SPK_RECOVERY_CLASS_REMAP_PASS")
        print(f"source_sha256={result['source_sha256']}")
        print(f"output_sha256={result['output_sha256']}")
        print(f"mapped_classes={result['mapped_classes']}")
        print(f"output_entries={result['output_entries']}")
        print(f"class_parse_errors={result['class_parse_errors']}")
        print(f"out={args.out}")
        if args.result_out:
            print(f"result_out={args.result_out}")
        return 0

    if args.cmd == "jar-remap":
        try:
            class_plan = (
                _load(args.class_plan)
                if args.class_plan
                else None
            )
            member_plan = (
                _load(args.member_plan)
                if args.member_plan
                else None
            )
            member_safety_report = (
                _load(args.member_safety_report)
                if args.member_safety_report
                else None
            )
            member_safety_acceptance = (
                _load(args.member_safety_acceptance)
                if args.member_safety_acceptance
                else None
            )
            result = remap_jar(
                args.source_jar,
                _load(args.index),
                class_plan,
                args.out,
                member_plan=member_plan,
                allow_package_resource_risk=(
                    args.allow_package_resource_risk
                ),
                rewrite_class_name_strings=(
                    args.rewrite_class_name_strings
                ),
                allow_member_reflection_risk=(
                    args.allow_member_reflection_risk
                ),
                member_safety_report=member_safety_report,
                member_safety_acceptance=member_safety_acceptance,
            )
            if args.result_out:
                write_result(result, args.result_out)
        except (
            RepackError,
            json.JSONDecodeError,
        ) as e:
            print(f"REFUSED: {e}", file=sys.stderr)
            return 2
        print("SPK_RECOVERY_JAR_REMAP_PASS")
        for key in (
            "source_sha256",
            "output_sha256",
            "mapped_classes",
            "mapped_members",
            "mapped_fields",
            "mapped_methods",
            "output_entries",
            "class_parse_errors",
        ):
            print(f"{key}={result[key]}")
        print(f"out={args.out}")
        if args.result_out:
            print(f"result_out={args.result_out}")
        return 0

    if args.cmd == "verify-remap":
        try:
            class_plan = (
                _load(args.class_plan)
                if args.class_plan
                else None
            )
            member_plan = (
                _load(args.member_plan)
                if args.member_plan
                else None
            )
            report = verify_transformed_jar(
                _load(args.source_index),
                args.output_jar,
                class_plan=class_plan,
                member_plan=member_plan,
            )
            write_verify_json(report, args.out)
        except (
            VerificationError,
            json.JSONDecodeError,
        ) as e:
            print(f"REFUSED: {e}", file=sys.stderr)
            return 2
        print(
            "SPK_RECOVERY_VERIFY_REMAP_PASS"
            if report["pass"]
            else "SPK_RECOVERY_VERIFY_REMAP_FAIL"
        )
        for k, v in report["summary"].items():
            print(f"{k}={v}")
        print(f"issues={len(report['issues'])}")
        print(f"out={args.out}")
        return 0 if report["pass"] else 1

    if args.cmd == "decompile":
        try:
            result = run_decompiler(
                args.input_jar,
                args.decompiler_jar,
                expected_decompiler_sha256=(
                    args.decompiler_sha256
                ),
                engine=args.engine,
                out_dir=args.out_dir,
                clean_out=args.clean_out,
            )
            if args.result_out:
                write_decompiler_json(
                    result,
                    args.result_out,
                )
        except DecompilerError as e:
            print(f"REFUSED: {e}", file=sys.stderr)
            return 2
        print("SPK_RECOVERY_DECOMPILE_PASS")
        print(f"engine={result['engine']}")
        print(f"input_sha256={result['input_sha256']}")
        print(
            f"decompiler_sha256={result['decompiler_sha256']}"
        )
        print(f"java_files={result['java_file_count']}")
        print(f"out_dir={args.out_dir}")
        if args.result_out:
            print(f"result_out={args.result_out}")
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())

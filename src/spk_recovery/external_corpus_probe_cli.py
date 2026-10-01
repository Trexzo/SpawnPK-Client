from __future__ import annotations

import argparse
import json
from pathlib import Path

from .external_corpus_probe import (
    DEFAULT_EXTERNAL_REPOSITORY,
    EXACT_V308_SHA256,
    ExternalCorpusProbeError,
    run_external_corpus_probe,
)


def _print_human(report: dict) -> None:
    print("SPK_EXTERNAL_CORPUS_PROBE_PASS")
    print(f"probe_id={report['probe_id']}")
    print(f"corpus_id={report['corpus_id']}")
    print(
        "external_repository="
        + report["external_corpus"]["repository"]
    )
    print(
        "external_revision="
        + report["external_corpus"]["revision"]
    )
    print(
        "external_corpus_sha256="
        + report["external_corpus"]["corpus_sha256"]
    )
    print(
        "exact_v308_sha256="
        + report["authority"]["exact_v308_sha256"]
    )
    summary = report["summary"]
    print(
        "SUMMARY "
        f"external={summary['external_scoped_classes']} "
        f"exact={summary['exact_scoped_classes']} "
        f"matched={summary['matched']} "
        f"structural={summary['structural_matches']} "
        f"inferred={summary['inferred_matches']} "
        f"descriptive={summary['descriptive_name_candidates']} "
        f"ambiguous={summary['ambiguous']} "
        f"unmatched_external={summary['unmatched_external']} "
        f"unmatched_exact={summary['unmatched_exact_v308']}"
    )
    print("promotes_names=false")
    print("copies_external_source=false")
    for row in report["candidates"]:
        print(
            "CANDIDATE "
            f"{row['external_path']} -> "
            f"{row['exact_v308_path']} "
            f"strategy={row['strategy']} "
            f"confidence={row['confidence']} "
            f"score={row['score']} "
            f"readable={row['external_readable_name']} "
            f"descriptive={str(row['external_name_is_descriptive']).lower()}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Research-only structural correlation between a compiled "
            "external SpawnPK readable corpus and exact v308 authority."
        )
    )
    parser.add_argument(
        "external_classes",
        type=Path,
        help=(
            "Compiled external class directory (for example "
            "build/classes/java/main) or a JAR containing those classes."
        ),
    )
    parser.add_argument(
        "exact_v308_jar",
        type=Path,
        help="Exact v308 client JAR authority.",
    )
    parser.add_argument(
        "--external-revision",
        required=True,
        help="Pinned lowercase 40-hex Git revision of the external corpus.",
    )
    parser.add_argument(
        "--external-repository",
        default=DEFAULT_EXTERNAL_REPOSITORY,
    )
    parser.add_argument(
        "--expected-exact-sha256",
        default=EXACT_V308_SHA256,
    )
    parser.add_argument(
        "--scope-prefix",
        default="rs/",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
    )
    args = parser.parse_args(argv)

    try:
        report = run_external_corpus_probe(
            external_classes=args.external_classes,
            exact_v308_jar=args.exact_v308_jar,
            external_revision=args.external_revision,
            expected_exact_sha256=args.expected_exact_sha256,
            external_repository=args.external_repository,
            scope_prefix=args.scope_prefix,
        )
    except ExternalCorpusProbeError as exc:
        parser.error(str(exc))

    _print_human(report)
    if args.json_out is not None:
        args.json_out.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        args.json_out.write_text(
            json.dumps(
                report,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"json_out={args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

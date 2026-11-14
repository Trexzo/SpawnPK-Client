#!/usr/bin/env python3
"""R386 one-layer, owner-local full-source build acceptance.

Requires a private, SHA-pinned kit and local JDK21. Never launches the game,
reads owner caches, removes staging files, or publishes source/binaries.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

KIT_NAME = 'R381-Reproducible-Build-Kit.zip'
REFERENCE_NAME = 'R381-Reference-Built.jar'
KIT_SHA = '902e3b583840073c095ea51c5fe5bee4034340ab92bd19dc7c36f3173f092f96'
REFERENCE_SHA = 'ed092c2e56967cee501c6e120f915ac10810cc9adb375cd9efba4e86d2dbebf3'
SOURCE_COUNT, CLASS_COUNT = 1277, 1388
RUNNER_SHA = '91dc181a70696ddb6d0d71dc407e5cdc7cd063d6c607f8b3e9421d10fb9a62a4'
COMPARATOR_SHA = '8233381e7f1fdaf95913d0777414dedaadb58de7e786ce3ba0f6025e474d728e'

class Refused(ValueError):
    pass


def hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def verify_private_files(root: Path, kit_sha: str = KIT_SHA,
                         reference_sha: str = REFERENCE_SHA) -> tuple[Path, Path]:
    paths = (root / KIT_NAME, root / REFERENCE_NAME)
    for path, expected in zip(paths, (kit_sha, reference_sha)):
        if not path.is_file() or path.is_symlink() or path.stat().st_size > 30_000_000:
            raise Refused('PRIVATE_FILE_MISSING_OR_UNSAFE: ' + path.name)
        if hash_file(path) != expected:
            raise Refused('PRIVATE_SHA256_MISMATCH: ' + path.name)
    return paths


def assess(build_report: dict, class_report: dict, expected_os: str) -> str:
    """Strict acceptance: no Windows claim from Linux or synthetic success."""
    if (build_report.get('source_sha256_verified') != SOURCE_COUNT or
        sorted(build_report.get('dependency_sha256_verified', [])) != ['R218.jar', 'R239_filtered.jar'] or
        build_report.get('generated_classfiles') != CLASS_COUNT or
        build_report.get('jar_sha256') != REFERENCE_SHA or
        build_report.get('private_source_release_approved') is not False or
        class_report.get('status') != 'EXACT_HASH_MATCH' or
        class_report.get('jar_reference_sha256') != REFERENCE_SHA or
        class_report.get('jar_candidate_sha256') != REFERENCE_SHA or
        class_report.get('class_count_candidate') != CLASS_COUNT):
        return 'R386_REFUSED_OR_DRIFT'
    if (expected_os == 'nt' and
        build_report.get('platform') == 'windows' and
        build_report.get('windows_full_compile_tested') is True and
        build_report.get('status') == 'R383_WINDOWS_PRIVATE_FULL_BUILD_PASS'):
        return 'R386_WINDOWS_FULL_BUILD_PASS'
    if (expected_os != 'nt' and
        build_report.get('platform') == 'non-windows' and
        build_report.get('windows_full_compile_tested') is False and
        build_report.get('status') == 'R383_LINUX_REFERENCE_REBUILD_PASS'):
        return 'R386_LINUX_REHEARSAL_PASS'
    return 'R386_REFUSED_OR_DRIFT'


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle-dir', type=Path,
                        default=Path(__file__).resolve().parents[2])
    parser.add_argument('--javac', type=Path, required=True)
    parser.add_argument('--out-dir', type=Path, required=True)
    args = parser.parse_args(argv)
    root = args.bundle_dir.resolve()
    output = args.out_dir.resolve()
    runner = root / 'tools/r383/verify_private_full_build.py'
    comparator = root / 'tools/r385/compare_local_build_jars.py'
    if output.exists() or output.is_symlink():
        print('R386_REFUSED_EXISTING_OUTPUT', file=sys.stderr)
        return 2
    try:
        kit, reference = verify_private_files(root)
        if not runner.is_file() or runner.is_symlink() or not comparator.is_file() or comparator.is_symlink():
            raise Refused('LOCAL_VERIFICATION_TOOL_MISSING_OR_UNSAFE')
        if hash_file(runner) != RUNNER_SHA or hash_file(comparator) != COMPARATOR_SHA:
            raise Refused('VERIFICATION_TOOL_SHA256_DRIFT')
        if not args.javac.is_file():
            raise Refused('JAVAC_NOT_FOUND')
    except (OSError, Refused) as exc:
        print('R386_PRECHECK_REFUSED: ' + str(exc), file=sys.stderr)
        return 2
    command = [sys.executable, str(runner), '--private-bundle', str(kit),
               '--javac', str(args.javac), '--out-dir', str(output)]
    try:
        build = subprocess.run(command, check=False, timeout=300)
        report_file = output / 'R383-Verification-Report.json'
        build_report = json.loads(report_file.read_text(encoding='utf-8')) if report_file.is_file() else {}
        jar = output / 'R383-Source-Built-From-Private-Kit.jar'
        class_report = {}
        compare_code = -1
        if jar.is_file():
            cmp_target = output / 'R386-Class-Comparison.json'
            cmp = subprocess.run([sys.executable, str(comparator), '--reference',
                str(reference), '--candidate', str(jar), '--output', str(cmp_target)],
                check=False, timeout=40)
            compare_code = cmp.returncode
            if cmp_target.is_file():
                class_report = json.loads(cmp_target.read_text(encoding='utf-8'))
        verdict = assess(build_report, class_report, os.name)
        if build.returncode or compare_code:
            verdict = 'R386_REFUSED_OR_DRIFT'
        if output.is_dir():
            result = {'status': verdict, 'platform': os.name,
                      'owner_windows_full_build_verified': verdict == 'R386_WINDOWS_FULL_BUILD_PASS',
                      'linux_rehearsal_verified': verdict == 'R386_LINUX_REHEARSAL_PASS',
                      'source_release_approved': False, 'game_runtime_tested': False,
                      'production_files_modified': False,
                      'source_count': build_report.get('source_sha256_verified'),
                      'class_count': build_report.get('generated_classfiles'),
                      'build_status': build_report.get('status'),
                      'class_comparison_status': class_report.get('status'),
                      'reference_jar_sha256': REFERENCE_SHA}
            (output / 'R386-Offline-Acceptance-Result.json').write_text(
                json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='utf-8')
            print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if verdict.endswith('_PASS') else 2
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        print('R386_EXECUTION_REFUSED: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())

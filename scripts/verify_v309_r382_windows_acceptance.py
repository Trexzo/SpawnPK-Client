"""R382: verify a private Windows scratch-test receipt without publishing recovered Java.

Public CI validates synthetic contracts only. The real Windows JSON stays on the
owner-controlled PC; a SHA pin in the public witness identifies its exact bytes.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path

JAR_SHA = 'ed092c2e56967cee501c6e120f915ac10810cc9adb375cd9efba4e86d2dbebf3'
R381_SOURCE_ZIP_SHA = 'c5350e964219a36f79584576ce60693d49eec0e5b0ee2138cfcab258aa47bca7'
EXPECTED_TESTS = tuple(sorted([
    'test_r369_order.py', 'test_r370_version.py', 'test_r371_rename.py',
    'test_r372_rename.py', 'test_r373_order.py', 'test_r374_receipt.py',
    'test_r375_directory.py', 'test_r376_directory.py',
    'test_r377_staging.py', 'test_r378_passive_lock.py',
    'test_r379_cooperative_lock.py', 'test_r380_folder_lock.py',
    'test_r381_session.py', 'test_serializer_contract.py',
    'test_store_contract.py',
]))
HEX64 = re.compile(r'[0-9a-f]{64}\Z')
SAFE_FLAGS = (
    'original_game_runtime_tested', 'full_1277_windows_compile_tested',
    'private_source_release_approved', 'safe_stage_cleanup_proven',
    'windows_privileged_symlink_tests_all_executed',
    'physical_power_loss_durability_proven', 'live_v312_modified',
)

class Refused(ValueError):
    pass

def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def validate_witness(w: dict) -> dict:
    expected = {
        'baseline_pr', 'repository', 'windows_tested_source_baseline',
        'baseline_r381_source_zip_sha256', 'baseline_r381_jar_sha256',
        'windows_fixture_zip_sha256', 'windows_results_sha256',
        'windows_real_source_sha_pins_checked', 'recovered_java_source_count',
        'windows_test_scripts_passed', 'windows_test_scripts_total',
        'windows_test_names', 'private_java_source_files_changed',
        'scope', 'windows_host_java_major', 'windows_host_os',
        'symlink_test_limitations', *SAFE_FLAGS,
    }
    if set(w) != expected:
        raise Refused('UNEXPECTED_WITNESS_SCHEMA')
    if (w['baseline_pr'] != 1176 or w['repository'] != 'Trexzo/SpawnPK-Client'
        or w['windows_tested_source_baseline'] != 'R381'
        or w['baseline_r381_source_zip_sha256'] != R381_SOURCE_ZIP_SHA
        or w['baseline_r381_jar_sha256'] != JAR_SHA
        or w['recovered_java_source_count'] != 1277
        or w['windows_real_source_sha_pins_checked'] != 10
        or w['windows_test_scripts_passed'] != 15
        or w['windows_test_scripts_total'] != 15
        or w['windows_test_names'] != list(EXPECTED_TESTS)
        or w['private_java_source_files_changed'] != []
        or w['scope'] != 'OWNER_WINDOWS_ISOLATED_SOURCE_BACKED_FIXTURE'
        or w['windows_host_java_major'] != 21
        or 'Windows' not in w['windows_host_os']
        or not isinstance(w['symlink_test_limitations'], list)
        or not w['symlink_test_limitations']
        or any(w[k] is not False for k in SAFE_FLAGS)):
        raise Refused('INVALID_RELEASE_OR_SCOPE_CLAIM')
    for k in ('windows_results_sha256','windows_fixture_zip_sha256'):
        if not isinstance(w[k], str) or not HEX64.fullmatch(w[k]):
            raise Refused('INVALID_SHA256')
    return {'status':'R382_PUBLIC_WITNESS_VALID','baseline':'R381',
            'owner_private_windows_tests':'15/15', 'full_game_runtime_tested':False}

def verify_results(result: dict, expected_sha: str | None = None,
                   raw: bytes | None = None) -> dict:
    if expected_sha is not None:
        if raw is None or not HEX64.fullmatch(expected_sha) or sha(raw) != expected_sha:
            raise Refused('WINDOWS_RESULTS_DIGEST_DRIFT')
    if (result.get('status') != 'R382_WINDOWS_SOURCE_TEST_PASS'
        or result.get('os') != 'nt'
        or result.get('private_sources_sha_checked') != 10
        or '21.' not in result.get('java','')
        or not isinstance(result.get('scripts'), list)
        or len(result['scripts']) != 15):
        raise Refused('WINDOWS_TEST_RESULT_MISMATCH')
    names = [x.get('test') for x in result['scripts']]
    if sorted(names) != list(EXPECTED_TESTS) or len(set(names)) != 15:
        raise Refused('WINDOWS_TEST_SET_DRIFT')
    if any(x.get('status') != 'PASS' or
           not isinstance(x.get('seconds'), (int,float)) or x['seconds'] < 0
           for x in result['scripts']):
        raise Refused('WINDOWS_TEST_FAILURE')
    return {'status':'R382_WINDOWS_RESULT_VALID','passed':len(names),
            'private_java_source_files_changed':0,
            'original_game_runtime_tested':False}

def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--witness',type=Path,required=True)
    parser.add_argument('--private-windows-results',type=Path)
    args=parser.parse_args()
    try:
        w=json.loads(args.witness.read_text('utf8'))
        report=validate_witness(w)
        if args.private_windows_results is not None:
            raw=args.private_windows_results.read_bytes()
            report['windows_result']=verify_results(json.loads(raw), w['windows_results_sha256'],raw)
    except (OSError,ValueError,TypeError,KeyError) as e:
        print(json.dumps({'status':'R382_REFUSED','reason':str(e)}))
        return 2
    print(json.dumps(report,sort_keys=True,indent=2))
    return 0

if __name__=='__main__': raise SystemExit(main())

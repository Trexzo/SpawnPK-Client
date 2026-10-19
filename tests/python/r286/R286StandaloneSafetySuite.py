#!/usr/bin/env python3
"""Verify R286 source-only Windows handoff without a Windows desktop or private game code.

Re-runs the actual bundled 19-case safety suite and independently inspects
source-only asset boundaries, SHA-256 manifest, and prior runtime evidence.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

PINNED_SHA = '2cacd2c551d6169be45e695f324d6c70a6d2a0b73a59b15fc5bce444f88a9877'
EXPECTED_JAR = 'dbaeaef9b375c8a99a6138075bed4ba71ef71ad2d82e8417ae36b400bd4828bd'

def check_archive(path):
    checks = 0
    def ck(ok, reason):
        nonlocal checks
        if not ok:
            raise AssertionError('R286_SAFETY_FAIL: ' + reason)
        checks += 1
    blob = Path(path).read_bytes()
    ck(hashlib.sha256(blob).hexdigest() == PINNED_SHA, 'unverified release archive')
    with zipfile.ZipFile(path) as z:
        ck(z.testzip() is None, 'CRC integrity')
        meta = json.loads(z.read('MANIFEST.json'))
        ck(meta['milestone'] == 'R286', 'milestone')
        ck(meta['native_windows_gui'] == 'NOT_TESTED', 'overstated Windows pass')
        ck(meta['production_changes'] == 0, 'unexpected game-source change')
        ck(meta['prior_source_built_client_sha256'] == EXPECTED_JAR, 'wrong private JAR pin')
        ck(set(meta['files']) | {'MANIFEST.json'} == set(z.namelist()), 'unlisted file')
        for name, details in meta['files'].items():
            data = z.read(name)
            ck(len(data) == details['bytes'], 'size: ' + name)
            ck(hashlib.sha256(data).hexdigest() == details['sha256'], 'SHA: ' + name)
            ck(not name.lower().endswith(('.class','.jar','.idx','.dat','.ttf','.otf')), 'private binary: ' + name)
            ck('..' not in Path(name).parts and not name.startswith('/'), 'unsafe ZIP member')
        with tempfile.TemporaryDirectory(prefix='r286-public-safety-') as work:
            base = Path(work)
            # Extract exact whitelisted paths, no owner archives or installation.
            for member in z.namelist():
                output = base / member
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(z.read(member))
            run = subprocess.run(
                [sys.executable, '-B', str(base/'tests/R286WindowsHarnessRegression.py')],
                cwd=base, text=True, capture_output=True, timeout=30,
            )
            ck(run.returncode == 0, 'bundled safety suite failure: ' + run.stderr[-1000:])
            ck('Ran 19 tests' in run.stderr and '\nOK\n' in run.stderr, 'not all 19 cases passed')
            refusal = subprocess.run(
                [sys.executable, '-B', str(base/'scripts/R286-Windows-Acceptance.py'),
                 '--r278', '/absent/r278.zip', '--r265','/absent/r265.zip',
                 '--assets','/absent/cache.zip', '--original','/absent/original.jar',
                 '--r230','/absent/r230.zip', '--output',str(base/'never-created')],
                cwd=base, text=True, capture_output=True, timeout=10,
            )
            ck(refusal.returncode != 0, 'missing files allowed')
            ck('R286_MISSING_INPUT' in refusal.stderr, 'missing-file denial not explicit')
            ck(not (base/'never-created').exists(), 'refused inputs created output folder')
        ck('R286_AUTHENTIC_OWNER_ARCHIVE_STAGE_PASS' in z.read('evidence/R286_REAL_STAGE_COMPILE.log').decode(), 'real asset staging log absent')
        ck('R286_AWT_JAVA11_COMPILATION_PASS classes=2' in z.read('evidence/R286_REAL_STAGE_COMPILE.log').decode(), 'Java11 compilation evidence absent')
        ck('checks=228' in z.read('evidence/R285_PRIOR_EVIDENCE_RECHECK.log').decode(), 'R285 GUI evidence absent')
    print(f'R286_PUBLIC_SAFETY_SUITE_PASS checks={checks} bundled_tests=19 real_windows=NOT_TESTED')

if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Usage: python R286StandaloneSafetySuite.py R286_SOURCE_ONLY.zip')
    check_archive(sys.argv[1])

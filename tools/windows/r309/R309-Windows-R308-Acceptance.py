#!/usr/bin/env python3
"""R309: owner-only SHA-pinned R308 native Windows acceptance.

Default is read-only. Only --run-native-gui can start the bounded R286
Windows test in an isolated home. No private binary/cache or download code.
The exact existing R297 readiness and GUI harness are reused unchanged,
except for tightly constrained, in-memory R308 archive and JAR substitutions.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
import types

ROOT = Path(__file__).resolve().parents[3]
ORIGINAL = ROOT/'tools/windows/r297/R297-Windows-R295-Acceptance.py'
READINESS_GIT_BLOB = 'd75c4937349503093f669947e21de3acbce0e9b0'
ORIGINAL_GIT_BLOB = '9ce5cb9e567abe582d76996dbf3a32e64baf6cb6'
ORIGINAL_SHA256 = '403f0c6db7ba23e5bb59a57fa029d85c541a25838fd6a213eb67ad0ccea06c72'
R308_ARCHIVE = 'SpawnPK_v309_R308_SCENE_PLACEMENT_BOUNDS_PRIVATE.zip'
R308_ARCHIVE_SHA256 = '977645c2ed90c0936815e9da5ca609ee23480176088137f8d3e7ee3b88654d6c'
R308_JAR_SHA256 = '501072d504a4e03a758f44aaa32f0990d3f1599662f6f6d2fa0d83a14e6fc314'
R308_JAR_MEMBER = 'R308_SOURCE_BUILT_CLASS_ONLY.jar'

PATCHES = (
    ("'SpawnPK_v309_R295_SCENE_HASH_BOUNDS_PRIVATE.zip'", "'"+R308_ARCHIVE+"'", 1),
    ("'277fb5016d60e5b36bb22cede2b3b2500b9773636f433c65774db18a34e401f6'", "'"+R308_ARCHIVE_SHA256+"'", 1),
    ("R295_JAR='f5b6f4b6ea3e5e8fc49e1cbe61197647ed7c1e238a49d935c77882cb40da2e35'", "R295_JAR='"+R308_JAR_SHA256+"'", 1),
    ('R295_SOURCE_BUILT_CLASS_ONLY.jar', R308_JAR_MEMBER, 4),
)

class R309Refusal(RuntimeError):
    pass

def git_blob_sha(payload: bytes) -> str:
    return hashlib.sha1(b'blob '+str(len(payload)).encode('ascii')+b'\0'+payload).hexdigest()

def read_pinned(path: Path, git_sha: str, sha256: str | None = None) -> bytes:
    if not path.is_file() or path.is_symlink():
        raise R309Refusal('R309_PINNED_PUBLIC_SOURCE_MISSING_OR_SYMLINK '+path.name)
    data = path.read_bytes()
    if git_blob_sha(data) != git_sha or (sha256 and hashlib.sha256(data).hexdigest() != sha256):
        raise R309Refusal('R309_PINNED_PUBLIC_SOURCE_HASH_MISMATCH '+path.name)
    return data

def rewrite_pinned_harness(payload: bytes) -> bytes:
    # Caller verifies both public SHA pins before applying these substitutions.
    source = payload.decode('utf-8')
    for old, new, expected_count in PATCHES:
        if source.count(old) != expected_count:
            raise R309Refusal('R309_SOURCE_ANCHOR_DRIFT '+old[:50])
        source = source.replace(old, new)
    if 'R295_SOURCE_BUILT_CLASS_ONLY.jar' in source:
        raise R309Refusal('R309_OLD_JAR_MEMBER_REMAINS')
    return source.encode('utf-8')

def compile_pinned(name: str, payload: bytes):
    module = types.ModuleType(name)
    module.__file__ = '<verified-public-source-'+name+'>'
    exec(compile(payload, module.__file__, 'exec'), module.__dict__)
    return module

def load_adapters(root: Path = ROOT):
    readiness = read_pinned(root/'tools/windows/r297/R297-Owner-Readiness.py', READINESS_GIT_BLOB)
    original = read_pinned(root/'tools/windows/r297/R297-Windows-R295-Acceptance.py',
                           ORIGINAL_GIT_BLOB, ORIGINAL_SHA256)
    return (compile_pinned('r297_readiness', readiness),
            compile_pinned('r309_r308_pinned_harness', rewrite_pinned_harness(original)))

def run(args=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input-dir', type=Path, required=True, help='Owner-only SHA-pinned archive directory')
    p.add_argument('--output', type=Path, required=True, help='New, non-existing native receipt directory')
    p.add_argument('--run-native-gui', action='store_true', help='Explicitly permit bounded Windows AWT input')
    a = p.parse_args(args)
    inp = a.input_dir.expanduser().absolute()
    out = a.output.expanduser().absolute()
    if a.run_native_gui and sys.platform != 'win32':
        raise R309Refusal('R309_REFUSE_NON_WINDOWS_GUI')
    readiness, harness = load_adapters()
    report, trusted = readiness.admission(inp, ORIGINAL, out, loader=lambda _: harness)
    report['milestone'] = 'R309'
    report['target'] = 'R308'
    report['source_pins'] = 'R297_SHA_PINNED_IN_MEMORY_ADAPTER'
    report['note'] = 'Original r295 transport key is pinned to R308 owner ZIP, not R295 client.'
    print('R309_R308_READINESS '+json.dumps(report, sort_keys=True), flush=True)
    if not report['ready']:
        return 2
    if not a.run_native_gui:
        print('R309_R308_PREFLIGHT_ONLY: no client launched; native Windows acceptance NOT_TESTED', flush=True)
        return 0
    if trusted is not harness or sys.platform != 'win32':
        raise R309Refusal('R309_REFUSE_UNTRUSTED_OR_NON_WINDOWS_GUI')
    # Original harness revalidates SHA pins, guarded Robot/foreground window,
    # 127.0.0.1-only socket, isolated scratch/output and cleanup.
    return int(harness.main(['--input-dir',str(inp),'--output',str(out),'--run-native-gui']))

if __name__ == '__main__':
    try:
        raise SystemExit(run())
    except (OSError, ValueError, R309Refusal) as error:
        print('R309_FAIL_CLOSED '+str(error), file=sys.stderr)
        raise SystemExit(1)

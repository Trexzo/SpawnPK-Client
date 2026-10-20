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
import stat
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
    # Windows Git autocrlf can change only line endings during checkout.
    # Accept CRLF solely when the canonical LF bytes match BOTH source pins.
    if b'\r' in data:
        data = data.replace(b'\r\n', b'\n')
        if b'\r' in data:
            raise R309Refusal('R309_INVALID_PUBLIC_SOURCE_LINE_ENDINGS '+path.name)
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

def has_reparse_attribute(path: Path) -> bool:
    """Refuse Win32 junctions/reparse points as well as ordinary symlinks."""
    info = path.lstat()
    return path.is_symlink() or bool(
        getattr(info, 'st_file_attributes', 0)
        & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0)
    )

def audit_inputs(input_dir: Path, harness):
    """Inventory every owner input without writes; only digest matches are PASS."""
    try:
        if has_reparse_attribute(input_dir) or not input_dir.is_dir():
            raise R309Refusal('R309_INPUT_INVENTORY_UNSAFE_DIRECTORY')
    except OSError as error:
        raise R309Refusal('R309_INPUT_INVENTORY_DIRECTORY_MISSING_OR_UNREADABLE') from error
    expected = {'r286': harness.R286, 'r295': harness.R295, **harness.OWNER}
    entries = []
    for key, (filename, digest) in expected.items():
        path = input_dir/filename
        try:
            if has_reparse_attribute(path):
                status = 'REPARSE_POINT_REFUSED'
            elif not path.is_file():
                status = 'NOT_REGULAR_FILE'
            else:
                try:
                    status = ('SHA256_PASS' if harness.sha256_file(path) == digest
                              else 'SHA256_MISMATCH')
                except OSError:
                    status = 'READ_ERROR'
        except FileNotFoundError:
            status = 'MISSING'
        except OSError:
            status = 'READ_ERROR'
        entries.append({'key': key, 'filename': filename, 'status': status})
    return {
        'milestone': 'R309',
        'target': 'R308',
        'kind': 'READ_ONLY_INPUT_INVENTORY_NOT_NATIVE_ACCEPTANCE',
        'inputs': entries,
        'total': len(entries),
        'verified': sum(x['status'] == 'SHA256_PASS' for x in entries),
        'all_verified': all(x['status'] == 'SHA256_PASS' for x in entries),
        'client_modified': False,
        'native_windows_gui': 'NOT_TESTED',
    }

def run(args=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input-dir', type=Path, help='Owner-only SHA-pinned archive directory')
    p.add_argument('--output', type=Path, help='New, non-existing native receipt directory')
    p.add_argument('--run-native-gui', action='store_true', help='Explicitly permit bounded Windows AWT input')
    p.add_argument('--inventory', action='store_true', help='Read-only status of all exact owner inputs (no GUI)')
    a = p.parse_args(args)
    if a.inventory and a.run_native_gui:
        raise R309Refusal('R309_INVENTORY_AND_GUI_MUTUALLY_EXCLUSIVE')
    if a.input_dir is None or (not a.inventory and a.output is None):
        p.error('--input-dir is required; --output is also required except in --inventory mode')
    inp = a.input_dir.expanduser().absolute()
    if a.run_native_gui and sys.platform != 'win32':
        raise R309Refusal('R309_REFUSE_NON_WINDOWS_GUI')
    readiness, harness = load_adapters()
    if a.inventory:
        report = audit_inputs(inp, harness)
        print('R309_R308_INPUT_INVENTORY '+json.dumps(report, sort_keys=True), flush=True)
        return 0 if report['all_verified'] else 2
    out = a.output.expanduser().absolute()
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

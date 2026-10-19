#!/usr/bin/env python3
"""R297: native Windows readiness admission for exact SHA-pinned R295 GUI test.

Default is read-only: checks R291 source provenance, all seven private input
hashes and overlays, local Java/Python dependencies, Win32 physical desktop,
port availability, and path safety. Prints one bounded JSON report on stdout.
Actual GUI can start ONLY with --run-native-gui after every gate passes.
No proprietary binary/cache/code is embedded in this release.
"""
from __future__ import annotations
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import stat
import subprocess
import sys
import types
import zipfile

R291_RELEASE = ('R297-Windows-R295-Acceptance.py',
 '403f0c6db7ba23e5bb59a57fa029d85c541a25838fd6a213eb67ad0ccea06c72')
R291_ENTRY = 'tools/windows/r297/R297-Windows-R295-Acceptance.py'
R291_ENTRY_SHA = '403f0c6db7ba23e5bb59a57fa029d85c541a25838fd6a213eb67ad0ccea06c72'


def sha256_file(path):
    h = hashlib.sha256()
    with path.open('rb') as inp:
        for block in iter(lambda: inp.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def load_pinned_r291(bundle):
    """Execute only known-byte public R291 code, never extracted owner input."""
    if not bundle.is_file() or bundle.is_symlink() or sha256_file(bundle) != R291_RELEASE[1]:
        raise ValueError('R292_R291_RELEASE_SHA256_MISMATCH_OR_MISSING')
    payload = bundle.read_bytes()
    if hashlib.sha256(payload).hexdigest() != R291_ENTRY_SHA:
        raise ValueError('R297_R295_GUI_ENTRY_SHA256_MISMATCH')
    module = types.ModuleType('pinned_r291_acceptance')
    module.__file__ = '<pinned-original-r297-source>'
    exec(compile(payload, module.__file__, 'exec'), module.__dict__)
    return module


def java_version(text):
    match = re.search(r'(?:javac\s+|(?:openjdk|java)\s+version\s+)["\s]*([0-9]+)(?:\.([0-9]+))?', text, re.I)
    if not match:
        return None
    first = int(match.group(1))
    return int(match.group(2)) if first == 1 and match.group(2) else first


def runtime_check():
    result = {'python': sys.version_info >= (3, 11)}
    try:
        from PIL import ImageGrab
        result['pillow'] = callable(ImageGrab.grab)
    except (ImportError, OSError, AttributeError):
        result['pillow'] = False
    for command in ('java', 'javac'):
        exe = shutil.which(command)
        if not exe:
            result[command] = False
            continue
        try:
            check = subprocess.run([exe, '-version'], stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True, timeout=6, check=False)
            major = java_version(check.stdout + '\n' + check.stderr)
            result[command] = check.returncode == 0 and major is not None and major >= 11
        except (OSError, subprocess.TimeoutExpired):
            result[command] = False
    return result


def windows_display():
    if sys.platform != 'win32':
        return {'ok': False, 'reason': 'Win32 interactive desktop required'}
    try:
        user32 = ctypes.WinDLL('user32', use_last_error=True)
        user32.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_void_p]
        user32.SetProcessDpiAwarenessContext.restype = ctypes.c_bool
        aware = user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        if not aware:
            # The process may already have the appropriate awareness configured.
            user32.GetThreadDpiAwarenessContext.argtypes = []
            user32.GetThreadDpiAwarenessContext.restype = ctypes.c_void_p
            user32.GetAwarenessFromDpiAwarenessContext.argtypes = [ctypes.c_void_p]
            user32.GetAwarenessFromDpiAwarenessContext.restype = ctypes.c_int
            current = user32.GetThreadDpiAwarenessContext()
            if not current or user32.GetAwarenessFromDpiAwarenessContext(current) != 2:
                return {'ok': False, 'reason': 'physical DPI awareness not provable'}
        user32.GetSystemMetrics.argtypes = [ctypes.c_int]
        user32.GetSystemMetrics.restype = ctypes.c_int
        user32.GetDpiForSystem.argtypes = []
        user32.GetDpiForSystem.restype = ctypes.c_uint
        width = int(user32.GetSystemMetrics(0))
        height = int(user32.GetSystemMetrics(1))
        dpi = int(user32.GetDpiForSystem())
        return {'ok': (width, height, dpi) == (1400, 900, 96),
                'width': width, 'height': height, 'dpi': dpi}
    except (AttributeError, OSError, ValueError) as exc:
        return {'ok': False, 'reason': type(exc).__name__}


def loopback_available():
    # No connection is made; the bind is closed immediately. R291/R286 retest.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(('127.0.0.1', 43594))
            return True
        except OSError:
            return False


def safe_output_ancestors(out):
    current = out.parent.absolute()
    while True:
        if current.is_symlink():
            return False, 'symbolic-link output ancestor'
        try:
            s = current.lstat()
            if getattr(s, 'st_file_attributes', 0) & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0):
                return False, 'Windows reparse-point output ancestor'
        except OSError:
            return False, 'unreadable output ancestor'
        if current == current.parent:
            break
        current = current.parent
    return True, 'output ancestors are ordinary directories'


def admission(input_dir, r291_release, output, *, loader=None, runtime=None,
              display=None, port=None, platform=None):
    """Deterministic with injectable *test-only* probes; CLI has fixed real probes."""
    loader = load_pinned_r291 if loader is None else loader
    runtime = runtime_check if runtime is None else runtime
    display = windows_display if display is None else display
    port = loopback_available if port is None else port
    platform = sys.platform if platform is None else platform
    checks = []
    def put(key, passed, detail):
        checks.append({'check': key, 'pass': bool(passed), 'detail': str(detail)})
    source = None
    try:
        source = loader(r291_release)
        put('r297_r295_gui_source_sha256', True, 'exact exact R297 R295 GUI source SHA256')
    except (ValueError, OSError, KeyError, zipfile.BadZipFile, SyntaxError) as exc:
        put('r291_original_source_sha256', False, type(exc).__name__)
    put('win32', platform == 'win32', 'native Microsoft Windows only')
    if source is not None:
        try:
            source.preflight(input_dir, output)
            put('seven_owner_archives_and_r295_overlay', True, 'all owner/private inputs and source anchors pinned')
        except (Exception,) as exc:
            put('seven_owner_archives_and_r290_overlay', False, str(exc)[:180])
        try:
            safe, reason = safe_output_ancestors(output)
            put('no_output_ancestor_reparse', safe, reason)
        except (Exception,) as exc:
            put('no_output_ancestor_reparse', False, type(exc).__name__)
    else:
        put('seven_owner_archives_and_r290_overlay', False, 'untrusted R291 source cannot be executed')
        put('no_output_ancestor_reparse', False, 'R291 source not verified')
    try:
        deps = runtime()
        for name in ('python','pillow','java','javac'):
            put(name, deps.get(name) is True, 'supported' if deps.get(name) else 'missing or unsupported')
    except (Exception,) as exc:
        for name in ('python','pillow','java','javac'):
            put(name, False, type(exc).__name__)
    if platform == 'win32':
        try:
            measured = display()
            put('primary_1400x900_96dpi', measured.get('ok') is True, json.dumps(measured,sort_keys=True))
        except (Exception,) as exc:
            put('primary_1400x900_96dpi',False,type(exc).__name__)
        try:
            put('localhost_43594_free', port() is True, '127.0.0.1 bind check')
        except OSError as exc:
            put('localhost_43594_free',False,type(exc).__name__)
    else:
        put('primary_1400x900_96dpi',False,'no Windows display measured')
        put('localhost_43594_free',False,'no Windows port readiness claimed')
    return {'milestone':'R297','kind':'NATIVE_GUI_PREREQUISITES_NOT_GAMEPLAY',
            'ready':all(c['pass'] for c in checks),'checks':checks,
            'checks_count':len(checks),'created_output':False,
            'client_modified':False,'native_windows_gui':'NOT_TESTED'},source


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--r291-source', type=Path)
    parser.add_argument('--run-native-gui', action='store_true', help='EXPLICIT real Windows AWT opt-in')
    args = parser.parse_args(argv)
    input_dir = args.input_dir.expanduser().absolute()
    output = args.output.expanduser().absolute()
    bundled_original = Path(__file__).resolve().parent/R291_RELEASE[0]
    default_original = bundled_original if bundled_original.is_file() else input_dir/R291_RELEASE[0]
    r291_source = (args.r297_source or default_original).expanduser().absolute()
    report, original = admission(input_dir,r291_source,output)
    print('R297_R295_READINESS '+json.dumps(report,sort_keys=True),flush=True)
    if not report['ready']:
        return 2
    if not args.run_native_gui:
        print('R297_R295_NATIVE_GUI_NOT_REQUESTED no game client launched',flush=True)
        return 0
    if sys.platform != 'win32':
        raise RuntimeError('R297_GUI_REQUIRES_REAL_NATIVE_WINDOWS')
    # Parent harness revalidates original SHA hashes and runtime guards, and
    # refuses existing output. Never import game bytes into GitHub/this bundle.
    return int(original.main(['--input-dir', str(input_dir),'--output',str(output),'--run-native-gui']))

if __name__=='__main__':
    try: raise SystemExit(main())
    except (OSError, ValueError, RuntimeError) as exc:
        print('R297_FAIL_CLOSED '+str(exc),file=sys.stderr)
        raise SystemExit(1)

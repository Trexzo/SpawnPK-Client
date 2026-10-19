#!/usr/bin/env python3
"""R287: read-only preflight for the unchanged R286 Windows GUI acceptance.

No game launch, output directories, extraction, network connection to game servers,
or automatic desktop changes. The actual R286 runner remains the authority for GUI
acceptance. Only the five exact owner archives and the released R286 source ZIP are
allowed as inputs. Results are written to stdout, not disk.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys

RELEASE = ('SpawnPK_v309_R286_WINDOWS_GUARDED_ACCEPTANCE_SOURCE_ONLY.zip',
           '2cacd2c551d6169be45e695f324d6c70a6d2a0b73a59b15fc5bce444f88a9877')
BOOTSTRAP = ('Invoke-R286-Guarded-Windows.ps1',
             '2186740003afb75df8dd79e2da6a721c121026733dc20ca087973f1d0cd70246')
ARCHIVES = {
    'r278': ('SpawnPK_v309_R278_FULL_SOURCE_OBJECT_AUTHORITY_GUARDS.zip',
             'e83f4211d96ffe4188807c79e50cc526eecbe020d010cdd8fecb4a10f2768280'),
    'r265': ('SpawnPK_v309_R265_UNIFIED_CACHE_R246_PLAYER_APPEARANCE_DIAGNOSTIC_PRIVATE.zip',
             '9579556ab5b941bb2697955e56cf4b9d43b68787a652c580a702228554b28dbb'),
    'assets': ('.spawnpk (4).zip',
               '8e15964f44b62a22d2c05f0ae2f63d45ddad42016c721e586cf55a82d35da565'),
    'original': ('client(20261015-104312).jar',
                 'ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38'),
    'r230': ('SpawnPK_v309_R230_AUTHENTIC_ASSETS_LOGIN_PRIVATE.zip',
             '5c21e5c643de759da80c4d18ebB6a49c84968d47a979caa33f7d4ad2170a7125'.lower()),
}


def file_sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def java_major(version_text):
    match = re.search(r'(?:javac\s+|(?:openjdk|java)\s+version\s+)["\s]*([0-9]+)(?:\.([0-9]+))?', version_text, re.I)
    if not match:
        return None
    first = int(match.group(1))
    return int(match.group(2)) if first == 1 and match.group(2) else first


def runtime_prerequisites():
    try:
        from PIL import Image as _pillow_image  # Check actual import, not just presence.
        pillow_ok = hasattr(_pillow_image, 'open')
    except (ImportError, OSError):
        pillow_ok = False
    report = {'python': sys.version_info.major == 3 and sys.version_info.minor >= 11,
              'pillow': pillow_ok}
    for program in ('java', 'javac'):
        path = shutil.which(program)
        if not path:
            report[program] = False
            continue
        try:
            result = subprocess.run([path, '-version'], capture_output=True, text=True,
                                    timeout=5, check=False)
            major = java_major(result.stdout + '\n' + result.stderr)
            report[program] = result.returncode == 0 and major is not None and major >= 11
        except (OSError, subprocess.TimeoutExpired):
            report[program] = False
    return report


def native_screen():
    """Probe the current native Windows PRIMARY screen without changing system settings.

    DPI awareness is set for this checker process only; the R286 GUI process has its
    own independent checks. Fail closed if DPI could be virtualized or ambiguous.
    """
    import ctypes
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2, introduced in Windows 10.
    try:
        user32.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_void_p]
        user32.SetProcessDpiAwarenessContext.restype = ctypes.c_bool
        ok = user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        if not ok:
            # Already configured by the host may still be fine, but the physical
            # display dimensions would be ambiguous. Report unknown/fail closed.
            return {'valid': False, 'reason': 'cannot establish DPI-aware process'}
    except (AttributeError, OSError):
        return {'valid': False, 'reason': 'DPI-aware API unavailable'}
    user32.GetSystemMetrics.argtypes = [ctypes.c_int]
    user32.GetSystemMetrics.restype = ctypes.c_int
    user32.GetDpiForSystem.argtypes = []
    user32.GetDpiForSystem.restype = ctypes.c_uint
    width, height = int(user32.GetSystemMetrics(0)), int(user32.GetSystemMetrics(1))
    dpi = int(user32.GetDpiForSystem())
    return {'valid': width == 1400 and height == 900 and dpi == 96,
            'width': width, 'height': height, 'dpi': dpi}


def local_port_free():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('127.0.0.1', 43594))
        except OSError:
            return False
    return True


def safe_future_output(path, input_dir):
    if path.exists() or path.is_symlink():
        return False, 'output already exists'
    if not path.is_absolute():
        return False, 'output must be absolute'
    parent = path.parent
    if not parent.is_dir() or parent.is_symlink():
        return False, 'output parent missing or symbolic link'
    resolved_parent = parent.resolve()
    resolved_input = input_dir.resolve()
    # A candidate below the archive directory is risky; the acceptance runner
    # may stage large private assets there, so reject overlap preemptively.
    if resolved_parent == resolved_input or resolved_input in resolved_parent.parents:
        return False, 'output nested in owner input folder'
    if path == Path(path.anchor) or path == Path.home() or path == resolved_input:
        return False, 'unsafe output destination'
    return True, 'safe, absent output candidate'


def readiness(input_dir, evidence, output, *, platform_name=None,
              prerequisites=None, screen_probe=None, port_probe=None,
              expectations=None):
    """Return a machine-readable advisory report. Test seams NEVER affect CLI pins."""
    platform_name = sys.platform if platform_name is None else platform_name
    prerequisites = runtime_prerequisites if prerequisites is None else prerequisites
    screen_probe = native_screen if screen_probe is None else screen_probe
    port_probe = local_port_free if port_probe is None else port_probe
    expectations = ARCHIVES if expectations is None else expectations
    checks = []
    def record(name, passed, detail):
        checks.append({'check': name, 'pass': bool(passed), 'detail': str(detail)})

    is_windows = platform_name == 'win32'
    record('native_windows', is_windows, 'Windows required; Linux cannot verify Win32 GUI')
    record('input_directory', input_dir.is_dir() and not input_dir.is_symlink(), 'owner archive directory')
    for label, (filename, digest) in {'r286_release': RELEASE, 'r286_bootstrap': BOOTSTRAP, **expectations}.items():
        path = evidence if label == 'r286_release' else input_dir / filename
        if not path.is_file() or path.is_symlink():
            record('sha256_'+label, False, 'required regular file absent or symbolic link: '+filename)
            continue
        try:
            good = file_sha256(path) == digest
            record('sha256_'+label, good, 'pinned SHA256 '+('PASS' if good else 'MISMATCH'))
        except OSError as exc:
            record('sha256_'+label, False, 'unreadable archive: '+type(exc).__name__)
    safe, why = safe_future_output(output, input_dir)
    record('new_output', safe, why)
    try:
        pre = prerequisites()
        for name in ('python', 'pillow', 'java', 'javac'):
            record(name, pre.get(name) is True, 'present and supported' if pre.get(name) else 'missing or unsupported')
    except Exception as exc:
        record('runtime_dependencies', False, type(exc).__name__)
    if is_windows:
        try:
            screen = screen_probe()
            record('primary_display', screen.get('valid') is True,
                   json.dumps(screen, sort_keys=True))
        except Exception as exc:
            record('primary_display', False, type(exc).__name__)
        try:
            record('loopback_port_43594', port_probe() is True,
                   'bind available for later localhost server')
        except OSError as exc:
            record('loopback_port_43594', False, type(exc).__name__)
    else:
        record('primary_display', False, 'not attempted off Windows')
        record('loopback_port_43594', False, 'Windows-specific readiness not asserted off Windows')
    return {'milestone': 'R287', 'type': 'READ_ONLY_ADVISORY_NOT_GUI_ACCEPTANCE',
            'client_modified': False, 'created_output': False,
            'ready': all(c['pass'] for c in checks), 'checks': checks}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input-dir', required=True, type=Path)
    p.add_argument('--r286-evidence', type=Path, default=None)
    p.add_argument('--output', required=True, type=Path,
                   help='proposed NEW acceptance output path (not created)')
    args = p.parse_args(argv)
    input_dir = args.input_dir.expanduser().absolute()
    evidence = (args.r286_evidence or input_dir / RELEASE[0]).expanduser().absolute()
    output = args.output.expanduser().absolute()
    report = readiness(input_dir, evidence, output)
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0 if report['ready'] else 2


if __name__ == '__main__':
    raise SystemExit(main())

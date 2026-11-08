"""R353 source-only admission helpers and disabled original-binary supervisor.

Do not interpret an operator flag as evidence of OS-level isolation. No original
client or network operation can be launched by this module in this package.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile
from verify_r352 import parse_console, PIN
from verify_receipt import ReceiptRefused

class PreflightRefused(RuntimeError): pass

def admit_original(jar):
    jar=Path(jar).resolve(strict=True)
    if not jar.is_file() or jar.stat().st_size!=17532075:
        raise PreflightRefused("R352_EXPECT_PINNED_V309_JAR_LENGTH")
    sha=hashlib.sha256()
    with jar.open("rb") as inp:
        for buf in iter(lambda:inp.read(65536),b""): sha.update(buf)
    if sha.hexdigest()!=PIN: raise PreflightRefused("R352_EXPECT_PINNED_V309_JAR_HASH")
    try:
        with zipfile.ZipFile(jar) as z:
            if len(z.infolist())<=10000 or "rs/gui/Launcher.class" not in z.namelist():
                raise PreflightRefused("R352_ORIGINAL_LAUNCHER_ENTRY_ABSENT")
    except zipfile.BadZipFile as exc: raise PreflightRefused("R352_BAD_JAR_ZIP") from exc
    return jar

def verify_classes(classes):
    classes=Path(classes).resolve(strict=True)
    for name in ("R352OriginalLaunchTrace.class","R351DeniedEndpointAudit.class"):
        if not (classes/name).is_file(): raise PreflightRefused("R352_MISSING_COMPILED_CLASS_"+name)
    return classes

def sanitize_env():
    env=os.environ.copy()
    for key in ("JAVA_TOOL_OPTIONS","_JAVA_OPTIONS","JDK_JAVA_OPTIONS","CLASSPATH"):
        env.pop(key,None)
    return env

def execute(*, jar, java, classes, scratch_root=None, observe_ms=3000):
    """Never launch the original JAR from this source-only R353 distribution.

    A caller-provided flag cannot independently establish an OS network sandbox,
    and importing this function must not bypass the safety requirement.
    """
    raise PreflightRefused("R353_ORIGINAL_RUNTIME_DISABLED_PENDING_OS_ISOLATION")


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--jar",required=True)
    p.add_argument("--java",required=True)
    p.add_argument("--classes",required=True)
    p.add_argument("--scratch-root")
    p.add_argument("--observe-ms",type=int,default=3000)
    p.add_argument("--i-confirm-os-isolation",action="store_true",
                   help="Explicit operator check: external OS-level deny-all isolation has already been configured")
    args=p.parse_args(argv)
    if not args.i_confirm_os_isolation:
        print(json.dumps({"status":"R352_BLOCKED","reason":"OS_ISOLATION_NOT_CONFIRMED"}))
        return 2
    try:
        result=execute(jar=args.jar,java=args.java,classes=args.classes,
                       scratch_root=args.scratch_root,observe_ms=args.observe_ms)
    except (OSError,ValueError,PreflightRefused,ReceiptRefused,subprocess.TimeoutExpired) as exc:
        print(json.dumps({"status":"R352_BLOCKED","reason":type(exc).__name__}))
        return 2
    print(json.dumps(result,sort_keys=True,indent=2))
    return 0

if __name__=="__main__": raise SystemExit(main())

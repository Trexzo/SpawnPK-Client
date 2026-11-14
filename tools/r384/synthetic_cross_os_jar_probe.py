#!/usr/bin/env python3
"""R384 public-only cross-platform canonical JAR metadata and javac smoke probe."""
from __future__ import annotations
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'r383'))
from verify_private_full_build import canonical_class_zipinfo


def main():
    javac=shutil.which('javac')
    if not javac: raise SystemExit('JDK21 javac unavailable')
    version=subprocess.run([javac,'-version'],text=True,capture_output=True,check=True).stdout.strip()
    if not version.startswith('javac 21'): raise SystemExit('JDK21 required: '+version)
    with tempfile.TemporaryDirectory(prefix='r384 public spaces ') as temp:
        root=Path(temp);src=root/'source';src.mkdir()
        (src/'Probe.java').write_text('public final class Probe { public static int value(){return 384;} }\n', encoding='utf-8')
        output=root/'class folder';output.mkdir()
        cmd=[javac,'--release','11','-proc:none','-g:none','-encoding','UTF-8','-d',str(output),str(src/'Probe.java')]
        cp=subprocess.run(cmd,capture_output=True,text=True,timeout=40)
        if cp.returncode:raise SystemExit('JAVAC_PROBE_FAILED: '+cp.stdout+cp.stderr)
        cls=output/'Probe.class'
        if not cls.is_file() or not cls.read_bytes().startswith(bytes.fromhex('CAFEBABE')):
            raise SystemExit('CLASS_PROBE_FAILED')
        jar=root/'probe.jar'
        with zipfile.ZipFile(jar,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
            z.writestr(canonical_class_zipinfo('Probe.class'),cls.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
        with zipfile.ZipFile(jar) as z:
            if len(z.infolist())!=1 or z.infolist()[0].create_system!=3:raise SystemExit('ZIP_CREATOR_OS_DRIFT')
            if z.read('Probe.class')!=cls.read_bytes(): raise SystemExit('ZIP_PAYLOAD_DRIFT')
        print(json.dumps({'status':'R384_PUBLIC_CROSS_OS_JAR_PROBE_PASS','os':os.name,'jdk':version,
                          'synthetic_sources':1,'synthetic_classes':1,'jar_zip_creator_os':3,
                          'private_sources_compiled':False,'windows_full_private_build_tested':False}))

if __name__=='__main__':main()

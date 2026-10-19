#!/usr/bin/env python3
"""Reproduce owner-private R290 from *unchanged* pinned R278 and R265 archives.

No game Java/source, cache, credentials or redistributable client assets are
embedded here. Temporary original source is removed after compilation. This
script never installs or launches a game or connects to an external server.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile

PIN_R278='e83f4211d96ffe4188807c79e50cc526eecbe020d010cdd8fecb4a10f2768280'
PIN_R265='9579556ab5b941bb2697955e56cf4b9d43b68787a652c580a702228554b28dbb'
PIN_R278_REBUILDER='8351858450127e5de5c07e9d601abeb01168ac8b416ac5c00e703204cd74cd42'
PIN_R278_JAR='dbaeaef9b375c8a99a6138075bed4ba71ef71ad2d82e8417ae36b400bd4828bd'
PIN_R278_SOURCE='319f893290473e6f144e04c89de6c7e48efaa03c8a10e6f2acd8a9e28c9aa959'
PIN_R290_SOURCE='b0a1ae721da4dc2e1b0bfb7ea6e434b2f8bc41126eb1bd1ec3f776c07f56772c'
PIN_R290_JAR='f2f914f12196705fd7233ea022742157d13deb50be85289465ce26b0dde3cd4a'
OLD='''        // Scene authority: reject stale/forged objects, not just sentinel inputs.
        if (n == -1 || n5 == -1) {
            return false;
        }'''
NEW='''        // Scene authority: reject missing entries and mismatched transmitted IDs.
        if (n == -1 || n5 == -1 || (n >>> 14 & 32767) != n4) {
            return false;
        }'''


def digest(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):
            h.update(block)
    return h.hexdigest()


def patched_client(prior: bytes) -> bytes:
    if hashlib.sha256(prior).hexdigest()!=PIN_R278_SOURCE:
        raise ValueError('R290_R278_SOURCE_PREIMAGE_MISMATCH')
    original=prior.decode('utf-8')
    if original.count(OLD)!=1 or original.find('private boolean handleObjectClick')>original.find(OLD):
        raise ValueError('R290_OBJECT_GUARD_ANCHOR_AMBIGUOUS')
    updated=original.replace(OLD,NEW).encode('utf-8')
    if hashlib.sha256(updated).hexdigest()!=PIN_R290_SOURCE:
        raise ValueError('R290_POSTIMAGE_SHA_MISMATCH')
    return updated


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--r278',required=True,type=Path,help='exact original owner R278 ZIP')
    p.add_argument('--r265',required=True,type=Path,help='exact original owner R265 ZIP')
    p.add_argument('--output',required=True,type=Path,help='new, absent private output directory')
    p.add_argument('--javac',default='javac')
    args=p.parse_args(argv)
    target=args.output.absolute()
    if target.exists() or target.is_symlink():
        raise FileExistsError('R290_REFUSE_EXISTING_OUTPUT '+str(target))
    if not target.parent.is_dir() or target.parent.is_symlink():
        raise FileNotFoundError('R290_OUTPUT_PARENT_UNSAFE_OR_MISSING')
    for label,path,expected in [('R278',args.r278,PIN_R278),('R265',args.r265,PIN_R265)]:
        if not path.is_file() or path.is_symlink() or digest(path)!=expected:
            raise ValueError('R290_PRIVATE_PINNED_INPUT_REFUSED '+label)
    with zipfile.ZipFile(args.r278) as old_archive:
        if old_archive.testzip():raise ValueError('R290_R278_CORRUPT_ZIP')
        script=old_archive.read('scripts/rebuild_r278.py')
        if hashlib.sha256(script).hexdigest()!=PIN_R278_REBUILDER:
            raise ValueError('R290_R278_REBUILDER_SHA_MISMATCH')
        if hashlib.sha256(old_archive.read('bin/R278_SOURCE_BUILT_CLASS_ONLY.jar')).hexdigest()!=PIN_R278_JAR:
            raise ValueError('R290_R278_BASE_JAR_SHA_MISMATCH')
    with tempfile.TemporaryDirectory(prefix='spawnpk-r290-private-build-') as temp:
        root=Path(temp)
        rebuild_script=root/'rebuild_r278.py';rebuild_script.write_bytes(script)
        spec=importlib.util.spec_from_file_location('r278_pinned',rebuild_script)
        r278=importlib.util.module_from_spec(spec);spec.loader.exec_module(r278)
        classes=root/'classes';classes.mkdir()
        deps=root/'deps';deps.mkdir()
        with zipfile.ZipFile(args.r265) as z:
            original=z.read('source/rs/Client.java')
            updated=patched_client(r278.patch(original))
            sources=[]
            for item in z.namelist():
                if not (item.startswith('source/') and item.endswith('.java')):continue
                destination=root/item;destination.parent.mkdir(parents=True,exist_ok=True)
                destination.write_bytes(updated if item=='source/rs/Client.java' else z.read(item))
                sources.append(destination)
            if len(sources)!=1277:raise ValueError('R290_JAVA_SOURCE_COUNT_DRIFT')
            with zipfile.ZipFile(z.open('dependencies/R239_EXACT_RUNTIME_LIB.jar')) as original_deps, zipfile.ZipFile(deps/'R239_compile_scope.jar','w') as fixed:
                for info in original_deps.infolist():
                    if info.filename not in r278.BAD:
                        fixed.writestr(info,original_deps.read(info))
            (deps/'R218_exact.jar').write_bytes(z.read('dependencies/R218_EXACT_LIBS_COMPILE_ONLY_PRIVATE.jar'))
        paths=root/'sources.txt';paths.write_text('\n'.join(map(str,sources))+'\n')
        cp=os.pathsep.join([str(deps/'R239_compile_scope.jar'),str(deps/'R218_exact.jar')])
        cmd=[args.javac,'-J-Xmx2200m','--release','11','-proc:none','-g:none','-encoding','UTF-8',
             '-sourcepath',str(root/'no_other_sources'),'-cp',cp,'-d',str(classes),'@'+str(paths)]
        print('R290_FULL_SOURCE_COMPILE_STARTED files=1277 java_target=11',flush=True)
        subprocess.run(cmd,check=True)
        jar=root/'R290_SOURCE_BUILT_CLASS_ONLY.jar'
        if r278.write_jar(classes,jar)!=1386:raise ValueError('R290_COMPILER_CLASS_COUNT_DRIFT')
        observed=digest(jar)
        if observed!=PIN_R290_JAR:
            raise ValueError('R290_REBUILT_JAR_SHA_MISMATCH got='+observed)
        target.mkdir()
        shutil.copyfile(jar,target/'R290_SOURCE_BUILT_CLASS_ONLY.jar')
        manifest={'milestone':'R290','java_source_files':1277,'compiled_classes':1386,
                  'java_target':11,'previous_source_sha256':PIN_R278_SOURCE,
                  'new_source_sha256':PIN_R290_SOURCE,'source_built_private_jar_sha256':PIN_R290_JAR,
                  'original_client_code_in_package':False,'native_windows_gui':'NOT_TESTED',
                  'change':'Scene hash object ID must match outgoing object ID for every object action.'}
        (target/'R290_BUILD_MANIFEST.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
        print('R290_DETERMINISTIC_PRIVATE_SOURCE_BUILD_PASS classes=1386 sha256='+observed,flush=True)
    return 0

if __name__=='__main__':raise SystemExit(main())

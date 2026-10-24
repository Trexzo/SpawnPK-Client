#!/usr/bin/env python3
"""Rebuild the original owner-private R305 client from exact pinned R304 provenance.

This public source-only wrapper modifies four scene-visibility loop tokens. Original
client source, jars, assets and credentials are never embedded or installed.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import shutil
import tempfile
from pathlib import Path

PIN_R304_BUILDER = '76b62cf4518b2afd3431fd5fcad9285809d6555df646348c9f0727608627fab7'
PIN_R304_SCENE = '839492e3d66ea546699f18338f09135e9787ff0c40ef193517cb18e68f8accd4'
PIN_R305_SCENE = 'dd02b8627053d7a9dc1c6f932cb34c5e78c4c5d21103a06ca169199f8b49f17e'
PIN_R305_JAR = 'df44dd354dd7df5c6cbbaa5d3093bfe1db6353009c921e7201068b94e15ceae1'
PATCHES = (
    ('var21 < activeDrawDistance', 'var21 <= activeDrawDistance', 1),
    ('var22 < activeDrawDistance', 'var22 <= activeDrawDistance', 1),
    ('(var20 + 1) % 31', '(var20 + 1) % 32', 2),
)

def digest(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1048576),b''):
            h.update(chunk)
    return h.hexdigest()

def patch_visibility_seams(prior: bytes) -> bytes:
    if hashlib.sha256(prior).hexdigest()!=PIN_R304_SCENE:
        raise ValueError('R305_SCENE_PREIMAGE_SHA_MISMATCH')
    text=prior.decode('utf-8')
    opening='   public static void setViewport('
    closing='   private static boolean method455('
    if text.count(opening)!=1 or text.count(closing)!=1:
        raise ValueError('R305_VISIBILITY_SECTION_ANCHOR_DRIFT')
    start=text.index(opening)
    end=text.index(closing,start)
    method=text[start:end]
    for old,new,expected in PATCHES:
        if method.count(old)!=expected or method.count(new)!=0:
            raise ValueError('R305_VISIBILITY_TOKEN_ANCHOR_DRIFT '+old)
        method=method.replace(old,new)
    updated=(text[:start]+method+text[end:]).encode('utf-8')
    if hashlib.sha256(updated).hexdigest()!=PIN_R305_SCENE:
        raise ValueError('R305_SCENE_POSTIMAGE_SHA_MISMATCH')
    return updated

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--r278',type=Path,required=True)
    p.add_argument('--r265',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--javac',default='javac')
    args=p.parse_args(argv)
    target=args.output.absolute()
    if target.exists() or target.is_symlink():raise FileExistsError('R305_REFUSE_EXISTING_OUTPUT')
    if not target.parent.is_dir() or target.parent.is_symlink():raise FileNotFoundError('R305_UNSAFE_OUTPUT_PARENT')
    script=Path(__file__).resolve().parents[1]/'r304'/'rebuild_r304_from_pinned.py'
    if not script.is_file() or script.is_symlink() or digest(script)!=PIN_R304_BUILDER:
        raise ValueError('R305_PINNED_R304_BUILDER_MISSING_OR_DRIFT')
    spec=importlib.util.spec_from_file_location('r305_exact_r304_builder',script)
    base=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(base)
    original=base.patch_visibility
    base.patch_visibility=lambda source:patch_visibility_seams(original(source))
    base.PIN_R304_JAR=PIN_R305_JAR  # Preserve all inherited source, class and archive gates.
    with tempfile.TemporaryDirectory(prefix='r305-private-builder-',dir=target.parent) as temp:
        stage=Path(temp)/'compiled'
        base.main(['--r278',str(args.r278),'--r265',str(args.r265),
                   '--output',str(stage),'--javac',args.javac])
        jar=stage/'R304_SOURCE_BUILT_CLASS_ONLY.jar'
        if not jar.is_file() or digest(jar)!=PIN_R305_JAR:
            raise ValueError('R305_COMPILED_JAR_SHA_MISMATCH')
        manifest_path=stage/'R304_BUILD_MANIFEST.json'
        manifest=json.loads(manifest_path.read_text())
        if manifest.get('compiled_classes')!=1386 or manifest.get('java_source_files')!=1277:
            raise ValueError('R305_SOURCE_OR_CLASS_COUNT_MISMATCH')
        manifest.update(milestone='R305',new_scene_sha256=PIN_R305_SCENE,
            source_built_private_jar_sha256=PIN_R305_JAR,
            change='Complete all viewport border cells and wrap 32 yaw bands correctly.')
        jar.rename(stage/'R305_SOURCE_BUILT_CLASS_ONLY.jar')
        manifest_path.unlink()
        (stage/'R305_BUILD_MANIFEST.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
        if target.exists():raise FileExistsError('R305_REFUSE_EXISTING_OUTPUT')
        shutil.move(str(stage),str(target))
    print('R305_FULL_SOURCE_BUILD_PASS java=1277 classes=1386 jar_sha256='+PIN_R305_JAR)
    return 0

if __name__=='__main__':raise SystemExit(main())

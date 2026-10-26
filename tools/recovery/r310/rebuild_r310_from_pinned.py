#!/usr/bin/env python3
"""R310 private full-source build overlay: SHA-pinned original-independent delivery.

Only tiny source-replacement anchors appear here. Private R278/R265 recovered
Java and proprietary dependencies are read owner-locally; never committed.
Compilation only: no game launch, external sockets or installation.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile

PIN_R309_BUILDER = '13dbb28e6bb981677b54a36a91294633216d234167fa095987e7db10e021d24f'
PIN_R309_SCENE = '245ff4d6ac3789b8e8a8c739a935e8d5904a2d6ab19c1f5f3f2041673cd7d932'
PIN_R310_SCENE = '63b3bc9d7b01f5337ca859616196f08af635f28dbf119caa11f55dadec43d4bc'
PIN_R310_JAR = 'ae8191810ad324b68495446e0da9f325157ccc719c1bc698a734643b8baba722'


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def patch_scene(source: bytes) -> bytes:
    if digest(source) != PIN_R309_SCENE:
        raise ValueError('R310_REQUIRES_EXACT_R309_SCENE_PREIMAGE')
    text = source.decode('utf-8')
    replacements = (
        ('if ((var7.field5279 >> 29 & 3) == 2 && var7.field1531 == var2 && var7.field1533 == var1) {',
         'if (var7 != null && (var7.field5279 >> 29 & 3) == 2 && var7.field1531 == var2 && var7.field1533 == var1) {', 1),
        ('if ((var6.field5279 >> 29 & 3) == 2 && var6.field1531 == var2 && var6.field1533 == var3) {',
         'if (var6 != null && (var6.field5279 >> 29 & 3) == 2 && var6.field1531 == var2 && var6.field1533 == var3) {', 3),
        ('if ((var6.field5279 >> 29 & 3) == 2 && var6.field1531 == var1 && var6.field1533 == var2) {',
         'if (var6 != null && (var6.field5279 >> 29 & 3) == 2 && var6.field1531 == var1 && var6.field1533 == var2) {', 1),
        ('''            if (var5.field5058[var6].field5279 == var4) {
               return var5.field5058[var6].field1537 & 0xFF;
            }''',
         '''            graphics_ object = var5.field5058[var6];
            if (object != null && object.field5279 == var4) {
               return object.field1537 & 0xFF;
            }''', 1),
        ('''            if (var11.field5058[var12].field1529 instanceof Model) {
               int var13 = ((Model)var11.field5058[var12].field1529).modelHeight;''',
         '''            graphics_ object = var11.field5058[var12];
            if (object != null && object.field1529 instanceof Model) {
               int var13 = ((Model)object.field1529).modelHeight;''', 1),
    )
    for old, new, count in replacements:
        if text.count(old) != count:
            raise ValueError('R310_SCENE_ANCHOR_OR_CARDINALITY_DRIFT')
        text = text.replace(old, new)
    post = text.encode('utf-8')
    if digest(post) != PIN_R310_SCENE:
        raise ValueError('R310_SCENE_POSTIMAGE_SHA_MISMATCH')
    return post


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--r278', type=Path, required=True)
    parser.add_argument('--r265', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--javac', default='javac')
    args = parser.parse_args(argv)
    output = args.output.absolute()
    if output.exists() or output.is_symlink() or not output.parent.is_dir() or output.parent.is_symlink():
        raise ValueError('R310_OUTPUT_MUST_BE_NEW_IN_EXISTING_SAFE_FOLDER')
    prev_script = Path(__file__).resolve().parents[1] / 'r309' / 'rebuild_r309_from_pinned.py'
    if not prev_script.is_file() or prev_script.is_symlink() or digest(prev_script.read_bytes()) != PIN_R309_BUILDER:
        raise ValueError('R310_PINNED_PUBLIC_R309_BUILDER_MISSING_OR_CHANGED')
    spec = importlib.util.spec_from_file_location('r310_reviewed_r309', prev_script)
    prev = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(prev)
    prior_patch = prev.patch_scene
    prev.patch_scene = lambda src: patch_scene(prior_patch(src))
    prev.R309_JAR = PIN_R310_JAR
    with tempfile.TemporaryDirectory(prefix='r310-full-private-', dir=output.parent) as temp:
        stage = Path(temp) / 'stage'
        prev.main(['--r278', str(args.r278), '--r265', str(args.r265),
                   '--output', str(stage), '--javac', args.javac])
        jar = stage / 'R309_SOURCE_BUILT_CLASS_ONLY.jar'
        if digest(jar.read_bytes()) != PIN_R310_JAR:
            raise ValueError('R310_FULL_CLIENT_JAR_SHA_MISMATCH')
        jar.rename(stage / 'R310_SOURCE_BUILT_CLASS_ONLY.jar')
        (stage / 'R309_BUILD_MANIFEST.json').unlink()
        (stage / 'R310_BUILD_MANIFEST.json').write_text(json.dumps({
            'milestone': 'R310', 'java_source_files': 1277,
            'compiled_classes': 1386, 'changed_original_source_paths': ['rs/Scene.java'],
            'scene_source_sha256': PIN_R310_SCENE, 'jar_sha256': PIN_R310_JAR,
            'native_windows_gpu': 'NOT_TESTED',
            'live_authenticated_gameplay': 'NOT_TESTED'
        }, sort_keys=True, indent=2) + '\n')
        shutil.move(str(stage), str(output))
    print('R310_FULL_SOURCE_REPLAY_PASS sources=1277 classfiles=1386 jar_sha256='+PIN_R310_JAR)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

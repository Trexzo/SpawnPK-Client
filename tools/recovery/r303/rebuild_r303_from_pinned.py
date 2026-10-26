#!/usr/bin/env python3
"""Build original R303 using the exact source-safe R302 rebuild, plus one lighting fix.

The private original source and binaries are never embedded or published.
Output is a new private directory; existing output is never overwritten.
"""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, os, shutil, tempfile
from pathlib import Path

R302_RECIPE_SHA = '55d25e83d84d692efbc263cd9fe72c0e6433d9a37d0da3d616c18119881d3002'
R302_SCENE_SHA = 'ec91cf02318dc26a80a4a5e5ee9e912feff8a66ee83e37e2d82b25ada321bc66'
R303_SCENE_SHA = 'ee0660154ab0e289448194a476fc6b2629ea83e1d99ba7477755e6f4885f93b6'
R303_JAR_SHA = 'a9ae098a79aac6c53eca5a986773b8c79f998b435d181bfde859c283a866b12b'
R303_NAME = 'R303_SOURCE_BUILT_CLASS_ONLY.jar'


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()


def patch_lighting(prior:bytes)->bytes:
    if hashlib.sha256(prior).hexdigest()!=R302_SCENE_SHA:
        raise ValueError('R303_SCENE_SOURCE_PREIMAGE_MISMATCH')
    s=prior.decode('utf-8')
    opening='   private void method1018(int var1, int var2, Model var3, int var4) {\n'
    closing='   private void method1770('
    if s.count(opening)!=1 or s.count(closing)!=1:
        raise ValueError('R303_METHOD_BOUNDARY_AMBIGUOUS')
    a=s.index(opening);b=s.index(closing,a)
    body=s[a:b]
    expected={
        'if (var1 < this.field5663)':1,
        'if (var4 < this.field5663)':1,
        'if (var1 < this.field5663 && var4 < this.field5664)':1,
        'if (var1 < this.field5663 && var4 > 0)':1,
    }
    for key,count in expected.items():
        if body.count(key)!=count:raise ValueError('R303_LIGHTING_LOOKUP_ANCHOR_DRIFT '+key)
    body=body.replace(opening,opening+
        '      // Ground-object lighting may run on the last tile of an authentic region.\n'
        '      if (!this.isSceneTileInBounds(var2, var1, var4)) {\n'
        '         return;\n'
        '      }\n')
    body=body.replace('if (var1 < this.field5663)', 'if (var1 < this.field5663 - 1)')
    body=body.replace('if (var4 < this.field5663)', 'if (var4 < this.field5664 - 1)')
    body=body.replace('if (var1 < this.field5663 && var4 < this.field5664)', 'if (var1 < this.field5663 - 1 && var4 < this.field5664 - 1)')
    body=body.replace('if (var1 < this.field5663 && var4 > 0)', 'if (var1 < this.field5663 - 1 && var4 > 0)')
    out=(s[:a]+body+s[b:]).encode('utf-8')
    if hashlib.sha256(out).hexdigest()!=R303_SCENE_SHA:
        raise ValueError('R303_SCENE_SOURCE_POSTIMAGE_MISMATCH')
    return out


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--r278',type=Path,required=True)
    p.add_argument('--r265',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--javac',default='javac')
    args=p.parse_args(argv)
    target=args.output.absolute()
    if target.exists() or target.is_symlink():raise FileExistsError('R303_REFUSE_EXISTING_OUTPUT')
    if not target.parent.is_dir() or target.parent.is_symlink():raise FileNotFoundError('R303_OUTPUT_PARENT_UNSAFE')
    source=Path(__file__).resolve().parents[1]/'r302'/'rebuild_r302_from_pinned.py'
    if not source.is_file() or source.is_symlink() or sha(source)!=R302_RECIPE_SHA:
        raise ValueError('R303_EXACT_PUBLIC_R302_BUILDER_REQUIRED')
    spec=importlib.util.spec_from_file_location('exact_source_safe_r302',source)
    baseline=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(baseline)
    inherited=baseline.patch_r302_scene_occluder_capacity
    def composed(original):return patch_lighting(inherited(original))
    baseline.patch_r302_scene_occluder_capacity=composed
    baseline.R302_JAR_SHA=R303_JAR_SHA  # Keep original compiler, dependency and class-count checks.
    with tempfile.TemporaryDirectory(prefix='r303-private-build-',dir=target.parent) as t:
        stage=Path(t)/'stage'
        args_list=['--r278',str(args.r278),'--r265',str(args.r265),'--output',str(stage),'--javac',args.javac]
        baseline.main(args_list)
        rebuilt=stage/'R302_SOURCE_BUILT_CLASS_ONLY.jar'
        if not rebuilt.is_file() or sha(rebuilt)!=R303_JAR_SHA:
            raise ValueError('R303_JAR_POSTIMAGE_SHA_MISMATCH')
        manifest=json.loads((stage/'R302_BUILD_MANIFEST.json').read_text())
        if manifest['compiled_classes']!=1386 or manifest['java_source_files']!=1277:
            raise ValueError('R303_JAVA_CLASS_COUNT_MISMATCH')
        manifest.update(milestone='R303',new_scene_sha256=R303_SCENE_SHA,
                        source_built_private_jar_sha256=R303_JAR_SHA,
                        change='Ground-object lighting handles region-edge neighbors without out-of-bounds tile reads.')
        rebuilt.rename(stage/R303_NAME)
        (stage/'R302_BUILD_MANIFEST.json').unlink()
        (stage/'R303_BUILD_MANIFEST.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
        if target.exists():raise FileExistsError('R303_REFUSE_EXISTING_OUTPUT')
        shutil.move(str(stage),str(target))
    print('R303_PRIVATE_SOURCE_BUILD_PASS classes=1386 sha256='+R303_JAR_SHA)
    return 0

if __name__=='__main__':raise SystemExit(main())

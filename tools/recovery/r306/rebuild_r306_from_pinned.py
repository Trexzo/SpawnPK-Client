#!/usr/bin/env python3
"""Rebuild R306 from exact owner-private archives and SHA-pinned R305 sources.

R306 repairs visibility-grid lifetime across zoom/radius changes and guards the
software draw traversal when the configured radius is smaller than 25 tiles.
No proprietary Java source, client classes or cache are present in this script.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import shutil
import tempfile
from pathlib import Path

R305_BUILDER_SHA = 'be05611ced1ab591383a59358cb97049a859c0a5ff75c804a0a736b9f53afaed'
R305_SOURCE_SHA = 'dd02b8627053d7a9dc1c6f932cb34c5e78c4c5d21103a06ca169199f8b49f17e'
R306_SOURCE_SHA = 'b8fa016278c1ef8def2866dbffd54bf3a78f7b3bb28985672e1609e7f6787a3d'
R306_JAR_SHA = '9db9e6f3b43fc894f2e62828a67c04b00d22292d5782c9b967e3da6be3c35b14'
DRAW_SIGNATURE = '   public void drawScene(int var1, int var2, int var3, int var4, int var5, int var6) {'
OLD_TILE_LOOKUP = 'tileVisibilityBand[var21 - cameraTileX + activeDrawDistance][var22 - cameraTileY + activeDrawDistance]'
DYNAMIC_REBUILD = '''
      // Zoom mode can change the active radius without a resize/alignViewport call.
      // Rebuild the visibility grid before the GPU pass or any software tile lookup.
      if (tileVisibility == null || tileVisibility[0][0].length != 2 * activeDrawDistance + 1) {
         setViewport(500, 800, viewportMaxX, viewportMaxY);
      }
'''
SAFE_TILE_LOOKUP = '''   // A smaller visibility radius can coexist with the legacy 25-tile render traversal.
   // Tiles outside its computed grid are not visible; never index past its boundary.
   private static boolean isVisibleSceneTile(int tileX, int tileY) {
      int x = tileX - cameraTileX + activeDrawDistance;
      int y = tileY - cameraTileY + activeDrawDistance;
      return tileVisibilityBand != null && x >= 0 && x < tileVisibilityBand.length
         && y >= 0 && y < tileVisibilityBand[x].length && tileVisibilityBand[x][y];
   }

'''

def digest(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()

def patch_radius_transition(original:bytes)->bytes:
    if hashlib.sha256(original).hexdigest()!=R305_SOURCE_SHA:
        raise ValueError('R306_SOURCE_PREIMAGE_SHA_MISMATCH')
    source=original.decode('utf-8')
    def replace_once(old,new):
        nonlocal source
        if source.count(old)!=1:
            raise ValueError('R306_RENDERER_ANCHOR_DRIFT '+old[:60])
        source=source.replace(old,new)
    replace_once(DRAW_SIGNATURE+'\n',DRAW_SIGNATURE+DYNAMIC_REBUILD)
    replace_once(OLD_TILE_LOOKUP,'isVisibleSceneTile(var21, var22)')
    replace_once(DRAW_SIGNATURE,SAFE_TILE_LOOKUP+DRAW_SIGNATURE)
    patched=source.encode('utf-8')
    if hashlib.sha256(patched).hexdigest()!=R306_SOURCE_SHA:
        raise ValueError('R306_SOURCE_POSTIMAGE_SHA_MISMATCH')
    return patched

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--r278',required=True,type=Path)
    parser.add_argument('--r265',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--javac',default='javac')
    args=parser.parse_args(argv)
    dest=args.output.absolute()
    if dest.exists() or dest.is_symlink():raise FileExistsError('R306_REFUSE_EXISTING_OUTPUT')
    if not dest.parent.is_dir() or dest.parent.is_symlink():raise FileNotFoundError('R306_UNSAFE_OUTPUT_PARENT')
    original_script=Path(__file__).resolve().parents[1]/'r305'/'rebuild_r305_from_pinned.py'
    if not original_script.is_file() or original_script.is_symlink() or digest(original_script)!=R305_BUILDER_SHA:
        raise ValueError('R306_R305_PUBLIC_BUILDER_SHA_DRIFT')
    spec=importlib.util.spec_from_file_location('r306_pinned_r305',original_script)
    base=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(base)
    base_original=base.patch_visibility_seams
    base.patch_visibility_seams=lambda source:patch_radius_transition(base_original(source))
    base.PIN_R305_JAR=R306_JAR_SHA
    with tempfile.TemporaryDirectory(prefix='r306-pinned-build-',dir=dest.parent) as scratch:
        stage=Path(scratch)/'build'
        base.main(['--r278',str(args.r278),'--r265',str(args.r265),
                   '--output',str(stage),'--javac',args.javac])
        jar=stage/'R305_SOURCE_BUILT_CLASS_ONLY.jar'
        if not jar.is_file() or digest(jar)!=R306_JAR_SHA:
            raise ValueError('R306_COMPILED_CLIENT_SHA_MISMATCH')
        original_manifest=stage/'R305_BUILD_MANIFEST.json'
        manifest=json.loads(original_manifest.read_text())
        if manifest.get('compiled_classes')!=1386 or manifest.get('java_source_files')!=1277:
            raise ValueError('R306_JAVA_SOURCE_COUNT_DRIFT')
        manifest.update(milestone='R306',new_scene_sha256=R306_SOURCE_SHA,
          source_built_private_jar_sha256=R306_JAR_SHA,
          change='Rebuild stale visibility grids on radius transition and bound software tile visibility.')
        jar.rename(stage/'R306_SOURCE_BUILT_CLASS_ONLY.jar')
        original_manifest.unlink()
        (stage/'R306_BUILD_MANIFEST.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
        if dest.exists():raise FileExistsError('R306_REFUSE_EXISTING_OUTPUT')
        shutil.move(str(stage),str(dest))
    print('R306_FULL_SOURCE_BUILD_PASS java=1277 classes=1386 jar_sha256='+R306_JAR_SHA)
    return 0

if __name__=='__main__':raise SystemExit(main())

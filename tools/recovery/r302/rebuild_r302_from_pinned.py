#!/usr/bin/env python3
"""Reproduce owner-private R295 from exact R278 and R265 archives.

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



R293_OLD='        Object object;\n        int n5 = this.field761.getHashAtTile(planeLevel, n3, n2, n);'
R293_NEW='        Object object;\n        // A menu may outlive its scene tile. Validate coordinates BEFORE scene-grid indexing.\n        if (n == -1 || n2 < 0 || n2 >= 104 || n3 < 0 || n3 >= 104 || planeLevel < 0 || planeLevel >= 4) {\n            return false;\n        }\n        int n5 = this.field761.getHashAtTile(planeLevel, n3, n2, n);'
PIN_R293_SOURCE='db1dfd4a4752fced78c2cb886bc50159eb8eeb8cc94d27c70b3d9e2ff1b1764c'
PIN_R293_JAR='0d0eedae92efe709b2d6eb49b1fc4432db174a6e68a7f06fd4fc2736d0f6cee9'

def r293_patch(base:bytes)->bytes:
    r290=patched_client(base)
    source=r290.decode('utf-8')
    if source.count(R293_OLD)!=1:raise ValueError('R293_BOUNDS_GUARD_ANCHOR_DRIFT')
    new=source.replace(R293_OLD,R293_NEW).encode('utf-8')
    if hashlib.sha256(new).hexdigest()!=PIN_R293_SOURCE:raise ValueError('R293_POSTIMAGE_DRIFT')
    return new

SCENE_PREIMAGE_SHA = '5757842cf0cea18bcd99667ddeba5150ec915e450308ca07ff45ee3922fdf6b1'
SCENE_POSTIMAGE_SHA = '24790fc3aac8676df95c1cd0f830f26bc6ad749cc87435f47b9eb69c9c8ef813'
R295_BASE_JAR_SHA = 'f5b6f4b6ea3e5e8fc49e1cbe61197647ed7c1e238a49d935c77882cb40da2e35'
SCENE_OLD = """   public int getHashAtTile(int var1, int var2, int var3, int var4) {
      Tile var5 = this.tiles[var1][var2][var3];"""
SCENE_NEW = """   public int getHashAtTile(int var1, int var2, int var3, int var4) {
      // A stale menu or scene query may reference a tile outside the region.
      // Preserve the existing -1 absence contract without indexing the grid.
      if (var1 < 0 || var1 >= this.tiles.length || var2 < 0 || var2 >= this.tiles[var1].length || var3 < 0 || var3 >= this.tiles[var1][var2].length) {
         return -1;
      }
      Tile var5 = this.tiles[var1][var2][var3];"""

def patch_scene(original: bytes) -> bytes:
    if hashlib.sha256(original).hexdigest() != SCENE_PREIMAGE_SHA:
        raise ValueError('R295_SCENE_PREIMAGE_HASH_MISMATCH')
    source = original.decode('utf-8')
    if source.count(SCENE_OLD) != 1:
        raise ValueError('R295_SCENE_METHOD_ANCHOR_MISMATCH')
    changed = source.replace(SCENE_OLD,SCENE_NEW).encode('utf-8')
    if hashlib.sha256(changed).hexdigest() != SCENE_POSTIMAGE_SHA:
        raise ValueError('R295_SCENE_POSTIMAGE_HASH_MISMATCH')
    return changed

# R298: preserve original read-only scene-query empty sentinels on stale coordinates.
R295_SCENE_POSTIMAGE_SHA = SCENE_POSTIMAGE_SHA
R298_SCENE_POSTIMAGE_SHA = '1999066509802862ba8c7ba0e4d54cabdf0cf8da64aabbc370439eda287ceada'
R298_JAR_SHA = 'be86b334f9ddc471cc7353f4a9493587c8a8317ded4a3a6e538f0ba96c08fbc9'
READ_ONLY_SCENE_QUERIES = {
    'method1154': ('var1','var2','var3'),
    'method1364': ('var1','var2','var3'),
    'method1249': ('var1','var2','var3'),
    'method2963': ('var1','var2','var3'),
    'method2829': ('var1','var2','var3'),
    'method2780': ('var1','var2','var3'),
    'method2827': ('var1','var2','var3'),
    'method2960': ('var1','var2','var3'),
    'method1551': ('var1','var2','var3'),
    'method2717': ('var3','var1','var2'),
    'getInteractiveObject': ('var3','var1','var2'),
    'method2918': ('var3','var2','var1'),
}
R298_SAFE_HELPER = """   // Read-only scene queries return the original empty sentinel for stale tiles.
   private Tile safeQueryTile(int plane, int x, int y) {
      if (plane < 0 || plane >= this.tiles.length || x < 0 || x >= this.tiles[plane].length || y < 0 || y >= this.tiles[plane][x].length) {
         return null;
      }
      return this.tiles[plane][x][y];
   }

"""

def patch_read_only_scene_queries(prior: bytes) -> bytes:
    import re
    if hashlib.sha256(prior).hexdigest() != R295_SCENE_POSTIMAGE_SHA:
        raise ValueError('R298_R295_SCENE_SOURCE_PREIMAGE_MISMATCH')
    source=prior.decode('utf-8')
    anchor='   public int method1154(int var1, int var2, int var3) {'
    if source.count(anchor)!=1 or 'safeQueryTile(' in source:
        raise ValueError('R298_SCENE_HELPER_ANCHOR_DRIFT')
    source=source.replace(anchor,R298_SAFE_HELPER+anchor)
    for name,coords in READ_ONLY_SCENE_QUERIES.items():
        pattern=(r'(public\s+\w+\s+'+re.escape(name)+
                 r'\(int var1, int var2, int var3\)\s*\{\s*Tile var\d+ = )'
                 +r'this\.tiles\['+coords[0]+r'\]\['+coords[1]+r'\]\['+coords[2]+r'\];')
        source,n=re.subn(pattern,r'\g<1>this.safeQueryTile('+', '.join(coords)+');',source)
        if n!=1:raise ValueError('R298_READ_QUERY_ANCHOR_DRIFT '+name+' matches='+str(n))
    post=source.encode('utf-8')
    if hashlib.sha256(post).hexdigest()!=R298_SCENE_POSTIMAGE_SHA:
        raise ValueError('R298_SCENE_SOURCE_POSTIMAGE_MISMATCH')
    return post

R299_SCENE_PREIMAGE_SHA = '1999066509802862ba8c7ba0e4d54cabdf0cf8da64aabbc370439eda287ceada'
R299_SCENE_POSTIMAGE_SHA = '007159b0b47058552150985c45f5b441df1a4bbd5a794bc41b6ad172bee8832e'
R299_JAR_SHA = '9c4d4350918c05c4a9f40d9372cab8c77088c76a43a32eb7f46b6974d57738cc'
R299_MUTATION_GUARDS = {'method251': ('int var1, int var2, int var3, int var4', ('var1', 'var2', 'var3')), 'method3478': ('int var1, int var2, int var3, int var4', ('var4', 'var3', 'var1')), 'method93': ('int var1, int var2, int var3, byte var4', ('var2', 'var1', 'var3')), 'method1252': ('int var1, int var2, int var3', ('var2', 'var3', 'var1')), 'method1390': ('int var1, int var2, int var3', ('var1', 'var2', 'var3')), 'method1152': ('int var1, int var2, int var3', ('var1', 'var3', 'var2')), 'method1627': ('int var1, int var2, int var3', ('var1', 'var2', 'var3'))}
R299_MUTATION_HELPER = '   // A queued scene mutation may outlive the tile to which it refers.\n   private boolean isSceneTileInBounds(int plane, int x, int y) {\n      return plane >= 0 && plane < this.tiles.length && x >= 0 && x < this.tiles[plane].length && y >= 0 && y < this.tiles[plane][x].length;\n   }\n\n'

def patch_scene_mutations(prior: bytes) -> bytes:
    if hashlib.sha256(prior).hexdigest()!=R299_SCENE_PREIMAGE_SHA:
        raise ValueError('R299_SCENE_PREIMAGE_MISMATCH')
    src=prior.decode('utf-8')
    anchor = '   private Tile safeQueryTile(int plane, int x, int y) {'
    if src.count(anchor)!=1 or 'isSceneTileInBounds(' in src:
        raise ValueError('R299_HELPER_ANCHOR_DRIFT')
    src=src.replace(anchor,R299_MUTATION_HELPER+anchor)
    for name,(signature,coords) in R299_MUTATION_GUARDS.items():
        old='   public void '+name+'('+signature+') {\n'
        if src.count(old)!=1:raise ValueError('R299_METHOD_ANCHOR_DRIFT '+name)
        new=old+'      if (!this.isSceneTileInBounds('+', '.join(coords)+')) {\n         return;\n      }\n'
        src=src.replace(old,new)
    post=src.encode('utf-8')
    if hashlib.sha256(post).hexdigest()!=R299_SCENE_POSTIMAGE_SHA:
        raise ValueError('R299_SCENE_POSTIMAGE_MISMATCH')
    return post

R300_SCENE_PREIMAGE_SHA = R299_SCENE_POSTIMAGE_SHA
R300_SCENE_POSTIMAGE_SHA = '85367ddd248e15192ef2bffa55ed764b48b67fedfb3378f9bf7d419337affca8'
R300_JAR_SHA = 'a3ece2b2be3559777c140c93fc5d4a33499ccf45d9c5172e1bc53e4f439a2371'


def patch_scene_entrypoints(prior: bytes) -> bytes:
    import re
    if hashlib.sha256(prior).hexdigest()!=R300_SCENE_PREIMAGE_SHA:
        raise ValueError('R300_SCENE_PREIMAGE_MISMATCH')
    source=prior.decode('utf-8')
    def replace_once(old,new):
        nonlocal source
        if source.count(old)!=1:
            raise ValueError('R300_SCENE_ANCHOR_DRIFT '+old[:60])
        source=source.replace(old,new)
    replace_once('   public void setPlane(int var1) {\n      this.plane = var1;',
      '   public void setPlane(int var1) {\n      if (var1 < 0 || var1 >= this.tiles.length) {\n         return;\n      }\n      this.plane = var1;')
    replace_once('   public void method3365(int var1, int var2) {\n      Tile var3 = this.tiles[0][var2][var1];',
      '   public void method3365(int var1, int var2) {\n      if (!this.isSceneTileInBounds(0, var2, var1)) {\n         return;\n      }\n      Tile var3 = this.tiles[0][var2][var1];')
    helper='   // Object insertion must reject an invalid plane or footprint before indexing tiles.\n   private boolean isSceneFootprintInBounds(int plane, int x, int y, int width, int height) {\n      return plane >= 0 && plane < this.tiles.length && width > 0 && height > 0\n         && x >= 0 && y >= 0 && x <= this.tiles[plane].length - width\n         && y <= this.tiles[plane][0].length - height;\n   }\n\n'
    replace_once('   private boolean isSceneTileInBounds(int plane, int x, int y) {',helper+'   private boolean isSceneTileInBounds(int plane, int x, int y) {')
    for name in ('method3408','method2959'):
        pattern=re.compile(r'(   private boolean '+name+r'\([\s\S]+?\n   \) \{)\n(      for \(int var\d+ = var2; var\d+ < var2 \+ var4; var\d+\+\+\) \{)')
        source,count=pattern.subn(r'\1\n      if (!this.isSceneFootprintInBounds(var1, var2, var3, var4, var5)) {\n         return false;\n      }\n\2',source)
        if count!=1:raise ValueError('R300_SCENE_INSERTION_ANCHOR_DRIFT '+name)
    changed=source.encode('utf-8')
    if hashlib.sha256(changed).hexdigest()!=R300_SCENE_POSTIMAGE_SHA:
        raise ValueError('R300_SCENE_POSTIMAGE_MISMATCH')
    return changed

R301_SCENE_PREIMAGE_SHA = R300_SCENE_POSTIMAGE_SHA
R301_SCENE_POSTIMAGE_SHA = '27ba14ea218df3f4c377f76809ccb749c45ef6dee02d628f262ab99f7e3d1e49'
R301_JAR_SHA = 'e741150b360e01f0adf098c977843507a7ff4cc9c872451cf6461415ed2f58da'
R301_SCENE_CAPACITY_OLD = "   private boolean isSceneFootprintInBounds(int plane, int x, int y, int width, int height) {"
R301_SCENE_CAPACITY_HELPER = """   // Tracked world objects have fixed-capacity live and reusable slot tables.
   // Reject exhaustion before inserting any tiles, so failed placements stay atomic.
   private boolean hasTrackedObjectCapacity() {
      return this.field5665 >= 0 && this.field5665 < this.field5666.length && this.field5665 < this.field5667.length;
   }

"""
R301_OLD_INSERTION_GUARD = """      if (!this.isSceneFootprintInBounds(var1, var2, var3, var4, var5)) {
         return false;
      }"""
R301_NEW_INSERTION_GUARD = R301_OLD_INSERTION_GUARD + """
      if (var11 && !this.hasTrackedObjectCapacity()) {
         return false;
      }"""

def patch_r301_scene_capacity(source_bytes:bytes)->bytes:
    if hashlib.sha256(source_bytes).hexdigest()!=R301_SCENE_PREIMAGE_SHA:
        raise ValueError('R301_SCENE_PREIMAGE_SHA_MISMATCH')
    src=source_bytes.decode('utf-8')
    if src.count(R301_SCENE_CAPACITY_OLD)!=1 or src.count(R301_OLD_INSERTION_GUARD)!=2:
        raise ValueError('R301_SCENE_CAPACITY_ANCHOR_DRIFT')
    src=src.replace(R301_SCENE_CAPACITY_OLD,R301_SCENE_CAPACITY_HELPER+R301_SCENE_CAPACITY_OLD)
    src=src.replace(R301_OLD_INSERTION_GUARD,R301_NEW_INSERTION_GUARD)
    result=src.encode('utf-8')
    if hashlib.sha256(result).hexdigest()!=R301_SCENE_POSTIMAGE_SHA:
        raise ValueError('R301_SCENE_POSTIMAGE_SHA_MISMATCH')
    return result

R302_SCENE_PREIMAGE_SHA = R301_SCENE_POSTIMAGE_SHA
R302_SCENE_POSTIMAGE_SHA = 'ec91cf02318dc26a80a4a5e5ee9e912feff8a66ee83e37e2d82b25ada321bc66'
R302_JAR_SHA = 'f3ce35078a1ebf07314de6c7335a9a9d66b990c587730fdf07a452f23bec5fae'
R302_STATIC_ANCHOR = '   public static void method345(int var0, int var1, int var2, int var3, int var4, int var5, int var6, int var7) {\n      Occluder var8 = new Occluder();'
R302_STATIC_REPLACEMENT = '   public static void method345(int var0, int var1, int var2, int var3, int var4, int var5, int var6, int var7) {\n      // The occluder table is fixed-capacity and shared across scene rebuilds.\n      // Reject a stale plane or exhausted slot before creating or storing entries.\n      if (field5681 == null || field5682 == null || var0 < 0 || var0 >= field5681.length || var0 >= field5682.length\n         || field5682[var0] == null || field5681[var0] < 0 || field5681[var0] >= field5682[var0].length) {\n         return;\n      }\n      Occluder var8 = new Occluder();'

def patch_r302_scene_occluder_capacity(source_bytes:bytes)->bytes:
    if hashlib.sha256(source_bytes).hexdigest()!=R302_SCENE_PREIMAGE_SHA:
        raise ValueError('R302_SCENE_PREIMAGE_SHA_MISMATCH')
    s=source_bytes.decode('utf-8')
    if s.count(R302_STATIC_ANCHOR)!=1:
        raise ValueError('R302_OCCLUDER_SOURCE_ANCHOR_DRIFT')
    patched=s.replace(R302_STATIC_ANCHOR,R302_STATIC_REPLACEMENT).encode('utf-8')
    if hashlib.sha256(patched).hexdigest()!=R302_SCENE_POSTIMAGE_SHA:
        raise ValueError('R302_SCENE_POSTIMAGE_SHA_MISMATCH')
    return patched

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--r278',required=True,type=Path,help='exact original owner R278 ZIP')
    p.add_argument('--r265',required=True,type=Path,help='exact original owner R265 ZIP')
    p.add_argument('--output',required=True,type=Path,help='new, absent private output directory')
    p.add_argument('--javac',default='javac')
    args=p.parse_args(argv)
    target=args.output.absolute()
    if target.exists() or target.is_symlink():
        raise FileExistsError('R302_REFUSE_EXISTING_OUTPUT '+str(target))
    if not target.parent.is_dir() or target.parent.is_symlink():
        raise FileNotFoundError('R302_OUTPUT_PARENT_UNSAFE_OR_MISSING')
    for label,path,expected in [('R278',args.r278,PIN_R278),('R265',args.r265,PIN_R265)]:
        if not path.is_file() or path.is_symlink() or digest(path)!=expected:
            raise ValueError('R302_PRIVATE_PINNED_INPUT_REFUSED '+label)
    with zipfile.ZipFile(args.r278) as old_archive:
        if old_archive.testzip():raise ValueError('R290_R278_CORRUPT_ZIP')
        script=old_archive.read('scripts/rebuild_r278.py')
        if hashlib.sha256(script).hexdigest()!=PIN_R278_REBUILDER:
            raise ValueError('R290_R278_REBUILDER_SHA_MISMATCH')
        if hashlib.sha256(old_archive.read('bin/R278_SOURCE_BUILT_CLASS_ONLY.jar')).hexdigest()!=PIN_R278_JAR:
            raise ValueError('R290_R278_BASE_JAR_SHA_MISMATCH')
    with tempfile.TemporaryDirectory(prefix='spawnpk-r302-private-build-') as temp:
        root=Path(temp)
        rebuild_script=root/'rebuild_r278.py';rebuild_script.write_bytes(script)
        spec=importlib.util.spec_from_file_location('r278_pinned',rebuild_script)
        r278=importlib.util.module_from_spec(spec);spec.loader.exec_module(r278)
        classes=root/'classes';classes.mkdir()
        deps=root/'deps';deps.mkdir()
        with zipfile.ZipFile(args.r265) as z:
            original=z.read('source/rs/Client.java')
            updated=r293_patch(r278.patch(original))
            scene_postimage=patch_r302_scene_occluder_capacity(patch_r301_scene_capacity(patch_scene_entrypoints(patch_scene_mutations(patch_read_only_scene_queries(patch_scene(z.read('source/rs/Scene.java')))))))
            sources=[]
            for item in z.namelist():
                if not (item.startswith('source/') and item.endswith('.java')):continue
                destination=root/item;destination.parent.mkdir(parents=True,exist_ok=True)
                destination.write_bytes(updated if item=='source/rs/Client.java' else scene_postimage if item=='source/rs/Scene.java' else z.read(item))
                sources.append(destination)
            if len(sources)!=1277:raise ValueError('R302_JAVA_SOURCE_COUNT_DRIFT')
            with zipfile.ZipFile(z.open('dependencies/R239_EXACT_RUNTIME_LIB.jar')) as original_deps, zipfile.ZipFile(deps/'R239_compile_scope.jar','w') as fixed:
                for info in original_deps.infolist():
                    if info.filename not in r278.BAD:
                        fixed.writestr(info,original_deps.read(info))
            (deps/'R218_exact.jar').write_bytes(z.read('dependencies/R218_EXACT_LIBS_COMPILE_ONLY_PRIVATE.jar'))
        paths=root/'sources.txt';paths.write_text('\n'.join(map(str,sources))+'\n')
        cp=os.pathsep.join([str(deps/'R239_compile_scope.jar'),str(deps/'R218_exact.jar')])
        cmd=[args.javac,'-J-Xmx2200m','--release','11','-proc:none','-g:none','-encoding','UTF-8',
             '-sourcepath',str(root/'no_other_sources'),'-cp',cp,'-d',str(classes),'@'+str(paths)]
        print('R302_FULL_SOURCE_COMPILE_STARTED files=1277 java_target=11',flush=True)
        subprocess.run(cmd,check=True)
        jar=root/'R302_SOURCE_BUILT_CLASS_ONLY.jar'
        if r278.write_jar(classes,jar)!=1386:raise ValueError('R302_COMPILER_CLASS_COUNT_DRIFT')
        observed=digest(jar)
        if observed!=R302_JAR_SHA:
            raise ValueError('R302_REBUILT_JAR_SHA_MISMATCH got='+observed)
        target.mkdir()
        shutil.copyfile(jar,target/'R302_SOURCE_BUILT_CLASS_ONLY.jar')
        manifest={'milestone':'R302','java_source_files':1277,'compiled_classes':1386,
                  'java_target':11,'previous_client_sha256':PIN_R293_SOURCE,
                  'new_scene_sha256':R302_SCENE_POSTIMAGE_SHA,'source_built_private_jar_sha256':observed,
                  'original_client_code_in_package':False,'native_windows_gui':'NOT_TESTED',
                  'change':'Static Scene occluder insertion rejects invalid planes, malformed counters and exhausted 500-entry capacity.'}
        (target/'R302_BUILD_MANIFEST.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
        print('R302_DETERMINISTIC_PRIVATE_SOURCE_BUILD_PASS classes=1386 sha256='+observed,flush=True)
    return 0

if __name__=='__main__':raise SystemExit(main())

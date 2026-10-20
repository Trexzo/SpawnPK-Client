#!/usr/bin/env python3
"""Source-only reproducible R308 scene placement bounds build from exact R307 recipe.

Requires the owner's original exact R278 and R265 archives; never embeds original
recovered Java source, game assets, cache, credentials or compiled client.
"""
from __future__ import annotations
import argparse,hashlib,importlib.util,json,re,shutil,tempfile
from pathlib import Path

PIN_R307_BUILDER='176c0322183f3180bed905d9fb71f3d0e3e9ed9098b46ab182a29aa92edd4140'
PIN_R307_SCENE='2ed273e3dd162a5b1884f776dfcec2460f49b732ea0206b6211aeca72b3ef092'
PIN_R308_SCENE='baa165aacae5d9408c21235bef656ab459b41e666906991ea49ed4622d23aeae'
PIN_R308_JAR='501072d504a4e03a758f44aaa32f0990d3f1599662f6f6d2fa0d83a14e6fc314'
PLACEMENT_COORDS={
 'method1909':('var1','var2','var3'),
 'method1890':('var1','var7','var3'),
 'method2219':('var10','var6','var4'),
 'method3074':('var4','var8','var2'),
 'addGroundDecoration':('var1','var7','var3'),
 'method1657':('var7','var1','var8'),
 'method1680':('var10','var6','var4'),
 'method3442':('var4','var8','var2'),
}

def sha(data):return hashlib.sha256(data).hexdigest()
def file_sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1024*1024),b''):h.update(c)
 return h.hexdigest()

def patch_placement_bounds(source):
 if sha(source)!=PIN_R307_SCENE:raise ValueError('R308_SCENE_PREIMAGE_SHA_MISMATCH')
 s=source.decode('utf-8')
 for method,coords in PLACEMENT_COORDS.items():
  pattern=r'(?m)^(   public void '+re.escape(method)+r'\([\s\S]*?\) \{\n)'
  found=list(re.finditer(pattern,s))
  if len(found)!=1:raise ValueError('R308_PLACEMENT_METHOD_ANCHOR_DRIFT '+method)
  guard='      if (!this.isSceneTileInBounds('+', '.join(coords)+')) {\n         return;\n      }\n'
  s=s[:found[0].end()]+guard+s[found[0].end():]
 result=s.encode('utf-8')
 if sha(result)!=PIN_R308_SCENE:raise ValueError('R308_SCENE_POSTIMAGE_SHA_MISMATCH')
 return result

def main(argv=None):
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--r278',required=True,type=Path)
 p.add_argument('--r265',required=True,type=Path)
 p.add_argument('--output',required=True,type=Path)
 p.add_argument('--javac',default='javac')
 a=p.parse_args(argv)
 output=a.output.absolute()
 if output.exists() or output.is_symlink():raise FileExistsError('R308_REFUSE_EXISTING_OUTPUT')
 if not output.parent.is_dir() or output.parent.is_symlink():raise FileNotFoundError('R308_UNSAFE_OUTPUT_PARENT')
 original=Path(__file__).resolve().parents[1]/'r307'/'rebuild_r307_from_pinned.py'
 if not original.is_file() or original.is_symlink() or file_sha(original)!=PIN_R307_BUILDER:
  raise ValueError('R308_ORIGINAL_R307_BUILDER_SHA_DRIFT')
 spec=importlib.util.spec_from_file_location('r308_exact_r307',original)
 base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
 prev=base.patch_scene
 base.patch_scene=lambda source:patch_placement_bounds(prev(source))
 base.JAR_SHA=PIN_R308_JAR
 with tempfile.TemporaryDirectory(prefix='r308-pinned-original-',dir=output.parent) as d:
  stage=Path(d)/'compiled'
  base.main(['--r278',str(a.r278),'--r265',str(a.r265),'--output',str(stage),'--javac',a.javac])
  original_jar=stage/'R307_SOURCE_BUILT_CLASS_ONLY.jar'
  if not original_jar.is_file() or file_sha(original_jar)!=PIN_R308_JAR:
   raise ValueError('R308_COMPILED_BINARY_SHA_MISMATCH')
  manifest_path=stage/'R307_BUILD_MANIFEST.json'
  manifest=json.loads(manifest_path.read_text())
  if manifest.get('compiled_classes')!=1386 or manifest.get('java_source_files')!=1277:
   raise ValueError('R308_PRIVATE_BUILD_CLASS_COUNT_DRIFT')
  manifest.update(milestone='R308',previous_scene_sha256=PIN_R307_SCENE,
   previous_client_sha256='f7d8e18a5e5d0b43e25b579388d06f035e0890dc8d595c41aac56bb316fc9dcf',new_scene_sha256=PIN_R308_SCENE,
   source_built_private_jar_sha256=PIN_R308_JAR,
   change='Eight scene placement entry points reject out-of-scene plane and coordinates before modifying tiles.')
  original_jar.rename(stage/'R308_SOURCE_BUILT_CLASS_ONLY.jar')
  manifest_path.unlink()
  (stage/'R308_BUILD_MANIFEST.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
  if output.exists():raise FileExistsError('R308_REFUSE_EXISTING_OUTPUT')
  shutil.move(str(stage),str(output))
 print('R308_FULL_SOURCE_BUILD_PASS java=1277 classes=1386 jar_sha256='+PIN_R308_JAR)
 return 0
if __name__=='__main__':raise SystemExit(main())

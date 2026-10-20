#!/usr/bin/env python3
"""Real private R304 class-only client from unchanged R303 source-safe builder.

No original source or game binaries are committed. All original R278/R265
inputs, inherited source postimages and exact output class-JAR SHA are required.
"""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, shutil, tempfile
from pathlib import Path

PIN_R303_RECIPE = 'c808781ffd77f80c9298092d41a2cc0d6df692143332589dea95a3b72b53e3a5'
PIN_R303_SOURCE = 'ee0660154ab0e289448194a476fc6b2629ea83e1d99ba7477755e6f4885f93b6'
PIN_R304_SOURCE = '839492e3d66ea546699f18338f09135e9787ff0c40ef193517cb18e68f8accd4'
PIN_R304_JAR = '1364d7be33147b5dbe9437f2222007402db449f9b1e4a244565680b608385f20'

def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for block in iter(lambda:f.read(1048576),b''): h.update(block)
 return h.hexdigest()

def patch_visibility(prior:bytes)->bytes:
 if hashlib.sha256(prior).hexdigest()!=PIN_R303_SOURCE:
  raise ValueError('R304_REAL_SCENE_PREIMAGE_MISMATCH')
 s=prior.decode('utf-8')
 def section(start,end):
  if s.count(start)!=1 or s.count(end)!=1:raise ValueError('R304_SCENE_METHOD_ANCHOR_AMBIGUOUS')
  lo=s.index(start);hi=s.index(end,lo)
  return lo,hi,s[lo:hi]
 def once(body,old,new,amount=1):
  if body.count(old)!=amount:raise ValueError('R304_SCENE_ANCHOR_DRIFT '+old[:75])
  return body.replace(old,new)
 lo,hi,body=section('   public static void setViewport(', '   private static boolean method455(')
 body=once(body,'      int[] var4 = new int[9];',
  '      // The active radius differs between software and GPU/extended visibility.\n'
  '      // Reject impossible radii before allocating large or negatively sized grids.\n'
  '      if (activeDrawDistance < 1 || activeDrawDistance > 50) {\n'
  '         activeDrawDistance = field5658;\n'
  '      }\n'
  '      int[] var4 = new int[9];')
 body=once(body,
  '      boolean[][][][] var16 = new boolean[9][32][activeDrawDistance * 2 + 3][activeDrawDistance * 2 + 3];',
  '      tileVisibility = new boolean[8][32][activeDrawDistance * 2 + 1][activeDrawDistance * 2 + 1];\n'
  '      boolean[][][][] var16 = new boolean[9][32][activeDrawDistance * 2 + 3][activeDrawDistance * 2 + 3];')
 body=once(body,'for (int var10 = -26; var10 <= 26; var10++)',
  'for (int var10 = -activeDrawDistance - 1; var10 <= activeDrawDistance + 1; var10++)')
 body=once(body,'for (int var11 = -26; var11 <= 26; var11++)',
  'for (int var11 = -activeDrawDistance - 1; var11 <= activeDrawDistance + 1; var11++)')
 body=once(body,'if (var21 + activeDrawDistance < 51 && var22 + activeDrawDistance < 51)',
  'if (var21 + activeDrawDistance < tileVisibility[var18][var20].length && var22 + activeDrawDistance < tileVisibility[var18][var20][0].length)')
 s=s[:lo]+body+s[hi:]
 lo,hi,body=section('   private void method56()', '   private boolean method356(')
 body=once(body,' + field5658',' + activeDrawDistance',6)
 body=once(body,'<= 50','< tileVisibilityBand.length',2)
 for idx in ('var18','var17','var7','var9'):
  body=once(body,f'if ({idx} > 50)',f'if ({idx} >= tileVisibilityBand.length)')
  body=once(body,f'{idx} = 50;',f'{idx} = tileVisibilityBand.length - 1;')
 s=s[:lo]+body+s[hi:]
 result=s.encode('utf-8')
 if hashlib.sha256(result).hexdigest()!=PIN_R304_SOURCE:
  raise ValueError('R304_REAL_SCENE_POSTIMAGE_MISMATCH')
 return result

def main(argv=None):
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--r278',required=True,type=Path)
 p.add_argument('--r265',required=True,type=Path)
 p.add_argument('--output',required=True,type=Path)
 p.add_argument('--javac',default='javac')
 args=p.parse_args(argv)
 target=args.output.absolute()
 if target.exists() or target.is_symlink():raise FileExistsError('R304_REFUSE_EXISTING_OUTPUT')
 if not target.parent.is_dir() or target.parent.is_symlink():raise FileNotFoundError('R304_UNSAFE_OUTPUT_PARENT')
 exact=Path(__file__).resolve().parents[1]/'r303'/'rebuild_r303_from_pinned.py'
 if not exact.is_file() or exact.is_symlink() or sha(exact)!=PIN_R303_RECIPE:
  raise ValueError('R304_R303_RECIPE_PIN_MISMATCH')
 spec=importlib.util.spec_from_file_location('r304_exact_original_r303',exact)
 base=importlib.util.module_from_spec(spec)
 spec.loader.exec_module(base)
 original=base.patch_lighting
 base.patch_lighting=lambda data:patch_visibility(original(data))
 base.R303_JAR_SHA=PIN_R304_JAR
 with tempfile.TemporaryDirectory(prefix='r304-pinned-private-',dir=target.parent) as temp:
  stage=Path(temp)/'compiled'
  base.main(['--r278',str(args.r278),'--r265',str(args.r265),'--output',str(stage),'--javac',args.javac])
  compiled=stage/'R303_SOURCE_BUILT_CLASS_ONLY.jar'
  if not compiled.is_file() or sha(compiled)!=PIN_R304_JAR:
   raise ValueError('R304_COMPILED_CLIENT_JAR_HASH_MISMATCH')
  mf=stage/'R303_BUILD_MANIFEST.json'
  data=json.loads(mf.read_text())
  if data.get('compiled_classes')!=1386 or data.get('java_source_files')!=1277:
   raise ValueError('R304_COMPILER_CLASS_COUNT_MISMATCH')
  data.update(milestone='R304',new_scene_sha256=PIN_R304_SOURCE,
    source_built_private_jar_sha256=PIN_R304_JAR,
    change='Radius-dependent viewport and occluder visibility indices for software/GPU distances 1 through 50.')
  compiled.rename(stage/'R304_SOURCE_BUILT_CLASS_ONLY.jar')
  mf.unlink()
  (stage/'R304_BUILD_MANIFEST.json').write_text(json.dumps(data,sort_keys=True,indent=2)+'\n')
  if target.exists():raise FileExistsError('R304_REFUSE_EXISTING_OUTPUT')
  shutil.move(str(stage),str(target))
 print('R304_FULL_SOURCE_BUILD_PASS java=1277 classes=1386 jar_sha256='+PIN_R304_JAR,flush=True)
 return 0

if __name__=='__main__':raise SystemExit(main())

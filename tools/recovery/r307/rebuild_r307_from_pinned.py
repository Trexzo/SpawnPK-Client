#!/usr/bin/env python3
"""R307: reproduce private client from exact R278/R265 archives and pinned public patches.

Changes only Scene cold initialization and Client GPU viewport alignment. Game
sources and proprietary class files are never written to a public repository.
"""
from __future__ import annotations
import argparse,hashlib,importlib.util,json,os,shutil,subprocess,tempfile,zipfile
from pathlib import Path

PUBLIC_SCRIPTS={
 'r302':('55d25e83d84d692efbc263cd9fe72c0e6433d9a37d0da3d616c18119881d3002','rebuild_r302_from_pinned.py'),
 'r303':('c808781ffd77f80c9298092d41a2cc0d6df692143332589dea95a3b72b53e3a5','rebuild_r303_from_pinned.py'),
 'r304':('76b62cf4518b2afd3431fd5fcad9285809d6555df646348c9f0727608627fab7','rebuild_r304_from_pinned.py'),
 'r305':('be05611ced1ab591383a59358cb97049a859c0a5ff75c804a0a736b9f53afaed','rebuild_r305_from_pinned.py'),
 'r306':('bd81a1079027dfbb48252bbb8c7ef607acaa1dca0493a064c78eba13641bede5','rebuild_r306_from_pinned.py'),
}
PRE_CLIENT='db1dfd4a4752fced78c2cb886bc50159eb8eeb8cc94d27c70b3d9e2ff1b1764c'
POST_CLIENT='f7d8e18a5e5d0b43e25b579388d06f035e0890dc8d595c41aac56bb316fc9dcf'
PRE_SCENE='b8fa016278c1ef8def2866dbffd54bf3a78f7b3bb28985672e1609e7f6787a3d'
POST_SCENE='2ed273e3dd162a5b1884f776dfcec2460f49b732ea0206b6211aeca72b3ef092'
JAR_SHA='00204d4b1fe557e64054520e7f22b54bf7094b617784639d50b95c8b8af77d94'
CLIENT_OLD='''        if (!GpuRenderer.isActive()) {
            Scene.setViewport(500, 800, viewportWidth, viewportHeight);
        }'''
CLIENT_NEW='''        // Software and GPU renderers share the Scene visibility grid.
        // Initialize it in both modes before the first scene frame.
        Scene.setViewport(500, 800, viewportWidth, viewportHeight);'''
SCENE_FIELD_OLD='private static boolean[][][][] tileVisibility = new boolean[8][32][51][51];'
SCENE_FIELD_NEW='private static boolean[][][][] tileVisibility;'
SCENE_DRAW_OLD='setViewport(500, 800, viewportMaxX, viewportMaxY);'
SCENE_DRAW_NEW='''setViewport(500, 800,
            viewportMaxX > 0 ? viewportMaxX : Client.viewportWidth,
            viewportMaxY > 0 ? viewportMaxY : Client.viewportHeight);'''

def digest_bytes(data):return hashlib.sha256(data).hexdigest()
def digest_file(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for part in iter(lambda:f.read(1048576),b''):h.update(part)
 return h.hexdigest()
def pinned_module(name,path,sha):
 if not path.is_file() or path.is_symlink() or digest_file(path)!=sha:
  raise ValueError('R307_PUBLIC_SCRIPT_SHA_REFUSED '+name)
 spec=importlib.util.spec_from_file_location('r307_'+name,path)
 m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 return m

def patch_client(prior):
 if digest_bytes(prior)!=PRE_CLIENT:raise ValueError('R307_CLIENT_PREIMAGE_SHA_MISMATCH')
 s=prior.decode('utf-8')
 if s.count(CLIENT_OLD)!=1:raise ValueError('R307_CLIENT_ALIGN_ANCHOR_DRIFT')
 out=s.replace(CLIENT_OLD,CLIENT_NEW).encode('utf-8')
 if digest_bytes(out)!=POST_CLIENT:raise ValueError('R307_CLIENT_POSTIMAGE_SHA_MISMATCH')
 return out

def patch_scene(prior):
 if digest_bytes(prior)!=PRE_SCENE:raise ValueError('R307_SCENE_PREIMAGE_SHA_MISMATCH')
 s=prior.decode('utf-8')
 for old,new in ((SCENE_FIELD_OLD,SCENE_FIELD_NEW),(SCENE_DRAW_OLD,SCENE_DRAW_NEW)):
  if s.count(old)!=1:raise ValueError('R307_SCENE_ANCHOR_DRIFT '+old[:50])
  s=s.replace(old,new)
 out=s.encode('utf-8')
 if digest_bytes(out)!=POST_SCENE:raise ValueError('R307_SCENE_POSTIMAGE_SHA_MISMATCH')
 return out

def main(argv=None):
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('--r278',type=Path,required=True)
 ap.add_argument('--r265',type=Path,required=True)
 ap.add_argument('--output',type=Path,required=True)
 ap.add_argument('--javac',default='javac')
 a=ap.parse_args(argv)
 target=a.output.absolute()
 if target.exists() or target.is_symlink():raise FileExistsError('R307_REFUSE_EXISTING_OUTPUT')
 if not target.parent.is_dir() or target.parent.is_symlink():raise FileNotFoundError('R307_OUTPUT_PARENT_UNSAFE')
 scripts={}
 base=Path(__file__).resolve().parents[1]
 for name,(sha,filename) in PUBLIC_SCRIPTS.items():
  scripts[name]=pinned_module(name,base/name/filename,sha)
 r302=scripts['r302']
 for name,path,sha in (('r278',a.r278,r302.PIN_R278),('r265',a.r265,r302.PIN_R265)):
  if not path.is_file() or path.is_symlink() or digest_file(path)!=sha:raise ValueError('R307_PRIVATE_INPUT_SHA_REFUSED '+name)
 with zipfile.ZipFile(a.r278) as z:
  if z.testzip():raise ValueError('R307_BAD_R278_ZIP')
  rebuild=z.read('scripts/rebuild_r278.py')
  if digest_bytes(rebuild)!=r302.PIN_R278_REBUILDER:raise ValueError('R307_ORIGINAL_REBUILDER_DRIFT')
  if digest_bytes(z.read('bin/R278_SOURCE_BUILT_CLASS_ONLY.jar'))!=r302.PIN_R278_JAR:raise ValueError('R307_R278_JAR_DRIFT')
 with tempfile.TemporaryDirectory(prefix='r307-original-sources-') as d:
  work=Path(d);(work/'classes').mkdir();(work/'deps').mkdir()
  oldscript=work/'original_r278.py';oldscript.write_bytes(rebuild)
  original=pinned_module('r278',oldscript,r302.PIN_R278_REBUILDER)
  with zipfile.ZipFile(a.r265) as z:
   if z.testzip():raise ValueError('R307_BAD_R265_ZIP')
   client=patch_client(r302.r293_patch(original.patch(z.read('source/rs/Client.java'))))
   scene=r302.patch_r302_scene_occluder_capacity(
     r302.patch_r301_scene_capacity(r302.patch_scene_entrypoints(
       r302.patch_scene_mutations(r302.patch_read_only_scene_queries(
         r302.patch_scene(z.read('source/rs/Scene.java')))))))
   scene=scripts['r303'].patch_lighting(scene)
   scene=scripts['r304'].patch_visibility(scene)
   scene=scripts['r305'].patch_visibility_seams(scene)
   scene=scripts['r306'].patch_radius_transition(scene)
   scene=patch_scene(scene)
   sources=[]
   for name in z.namelist():
    if not(name.startswith('source/') and name.endswith('.java')):continue
    p=work/name;p.parent.mkdir(parents=True,exist_ok=True)
    p.write_bytes(client if name=='source/rs/Client.java' else scene if name=='source/rs/Scene.java' else z.read(name))
    sources.append(p)
   if len(sources)!=1277:raise ValueError('R307_SOURCE_COUNT_DRIFT')
   with zipfile.ZipFile(z.open('dependencies/R239_EXACT_RUNTIME_LIB.jar')) as before,zipfile.ZipFile(work/'deps/R239_filtered.jar','w') as after:
    for entry in before.infolist():
     if entry.filename not in original.BAD:after.writestr(entry,before.read(entry))
   (work/'deps/R218.jar').write_bytes(z.read('dependencies/R218_EXACT_LIBS_COMPILE_ONLY_PRIVATE.jar'))
  sourcefile=work/'sources.txt';sourcefile.write_text('\n'.join(map(str,sources))+'\n')
  cp=os.pathsep.join((str(work/'deps/R239_filtered.jar'),str(work/'deps/R218.jar')))
  cmd=[a.javac,'-J-Xmx2200m','--release','11','-proc:none','-g:none','-encoding','UTF-8','-sourcepath',str(work/'unused'),'-cp',cp,'-d',str(work/'classes'),'@'+str(sourcefile)]
  print('R307_FULL_SOURCE_BUILD_STARTED sources=1277',flush=True)
  subprocess.run(cmd,check=True)
  jar=work/'R307_SOURCE_BUILT_CLASS_ONLY.jar'
  if original.write_jar(work/'classes',jar)!=1386:raise ValueError('R307_CLASS_COUNT_DRIFT')
  if digest_file(jar)!=JAR_SHA:raise ValueError('R307_JAR_SHA_MISMATCH')
  target.mkdir()
  shutil.copyfile(jar,target/jar.name)
  manifest={'milestone':'R307','java_source_files':1277,'compiled_classes':1386,'java_target':11,
   'previous_client_sha256':PRE_CLIENT,'new_client_sha256':POST_CLIENT,
   'previous_scene_sha256':PRE_SCENE,'new_scene_sha256':POST_SCENE,
   'source_built_private_jar_sha256':JAR_SHA,'original_client_code_in_package':False,'native_windows_gui':'NOT_TESTED',
   'change':'Initialize GPU viewport and lazily compute cold Scene visibility before rendering.'}
  (target/'R307_BUILD_MANIFEST.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
  print('R307_FULL_SOURCE_BUILD_PASS classes=1386 jar_sha256='+JAR_SHA,flush=True)
 return 0

if __name__=='__main__':raise SystemExit(main())

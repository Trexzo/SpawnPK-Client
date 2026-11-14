#!/usr/bin/env python3
"""Public Windows/Ubuntu scratch-only javac 21 @argfile smoke test."""
import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path
from zipfile import ZipFile
from verify_private_full_build import javac_arg_path, Refused

def main():
 javac=shutil.which('javac')
 if not javac:raise SystemExit('javac missing')
 version=subprocess.run([javac,'-version'],capture_output=True,text=True,check=True).stdout.strip()
 if not version.startswith('javac 21'):raise SystemExit('JDK 21 required: '+version)
 with tempfile.TemporaryDirectory(prefix='r383 synthetic javac space path ') as rootstr:
  root=Path(rootstr);src=root/'source space'/'rs';src.mkdir(parents=True)
  (src/'Alpha.java').write_text('package rs; public class Alpha { public static int x(){return 2;} }\n',encoding='utf8')
  (src/'Beta.java').write_text('package rs; public class Beta { public static int y(){return Alpha.x()+1;} }\n',encoding='utf8')
  classes=root/'classes with spaces';classes.mkdir()
  args=root/'source args.txt';args.write_text('\n'.join(javac_arg_path(s) for s in sorted(src.glob('*.java')))+'\n',encoding='utf8')
  proc=subprocess.run([javac,'--release','11','-proc:none','-g:none','-encoding','UTF-8','-d',str(classes),'@'+str(args)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf8',errors='replace',timeout=45)
  if proc.returncode!=0:raise SystemExit('R383_SYNTHETIC_JAVAC_FAILED: '+proc.stdout)
  files=sorted(classes.rglob('*.class'))
  if len(files)!=2 or not all(p.read_bytes().startswith(bytes.fromhex('CAFEBABE')) for p in files):
   raise SystemExit('R383_SYNTHETIC_CLASS_COUNT_OR_MAGIC_CHANGED')
  print(json.dumps({'status':'R383_PUBLIC_SYNTHETIC_JAVAC_21_PASS','os':os.name,'compiler':version,'synthetic_sources':2,'synthetic_classes':2,'private_source_compiled':False,'game_launched':False}))
if __name__=='__main__':main()

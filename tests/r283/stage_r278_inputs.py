#!/usr/bin/env python3
"""Stage exact owner archives into a disposable regression home, no installs/network."""
import hashlib,sys,zipfile
from pathlib import Path
R265='9579556ab5b941bb2697955e56cf4b9d43b68787a652c580a702228554b28dbb'
ASSETS='8e15964f44b62a22d2c05f0ae2f63d45ddad42016c721e586cf55a82d35da565'
JAR='dbaeaef9b375c8a99a6138075bed4ba71ef71ad2d82e8417ae36b400bd4828bd'
CONFIG='073a7802afc64c76c8efd179a6a0c408c2f8c05dd686f1088efd7922807a0c79'

def sha(data):return hashlib.sha256(data).hexdigest()
def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def extract_config(dat,idx):
 offset=12
 size=int.from_bytes(idx[offset:offset+3],'big');sector=int.from_bytes(idx[offset+3:offset+6],'big')
 if not 0<size<2_000_000:raise RuntimeError('incorrect config record')
 observed=set();out=bytearray();seq=0
 while len(out)<size:
  if not sector or sector in observed:raise RuntimeError('cyclic config sector')
  observed.add(sector);off=sector*520;block=dat[off:off+520]
  if len(block)<520 or int.from_bytes(block[:2],'big')!=2 or int.from_bytes(block[2:4],'big')!=seq or block[7]!=1:
   raise RuntimeError('wrong cache sector identity')
  out.extend(block[8:8+min(512,size-len(out))]);sector=int.from_bytes(block[4:7],'big');seq+=1
 raw=bytes(out)
 if sha(raw)!=CONFIG:raise RuntimeError('config hash mismatch')
 return raw

def main():
 if len(sys.argv)!=5:raise SystemExit('Usage: stage_r278_inputs.py R278_EVIDENCE.zip R265_PRIVATE.zip .spawnpk_PRIVATE.zip WORKDIR')
 artifact,r265,assets,root=(Path(x) for x in sys.argv[1:]);root.mkdir(parents=True,exist_ok=True)
 if digest(r265)!=R265 or digest(assets)!=ASSETS:raise RuntimeError('owner input archive SHA256 mismatch')
 with zipfile.ZipFile(artifact) as z:
  out=root/'R278_SOURCE_BUILT_CLASS_ONLY.jar';out.write_bytes(z.read('bin/R278_SOURCE_BUILT_CLASS_ONLY.jar'))
  if digest(out)!=JAR:raise RuntimeError('R278 JAR SHA256 mismatch')
 with zipfile.ZipFile(r265) as z:
  for name in ['R239_EXACT_RUNTIME_LIB.jar','R218_EXACT_LIBS_COMPILE_ONLY_PRIVATE.jar']:
   (root/name).write_bytes(z.read('dependencies/'+name))
 with zipfile.ZipFile(assets) as z:
  config=extract_config(z.read('.spawnpk/main_file_cache.dat'),z.read('.spawnpk/main_file_cache.idx0'))
  (root/'config.bin').write_bytes(config)
  for name in ['loc.dat','loc.idx','osrs_loc.dat','osrs_loc.idx']:
   path=root/'home/.spawnpk'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(z.read('.spawnpk/'+name))
  for name in ['o.bin','e.bin']:
   path=root/'home/.spawnpk/configs'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(z.read('.spawnpk/configs/'+name))
  for name in ['loc.dat','loc.idx']:
   path=root/'home/.spawnpk/osrs_config'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(z.read('.spawnpk/osrs_config/'+name))
 print('R278_PRIVATE_INPUTS_SHA256_PASS config='+CONFIG+' java_jar='+JAR,flush=True)
if __name__=='__main__':main()

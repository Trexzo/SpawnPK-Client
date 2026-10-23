"""Synthetic Java9 proof of a JVM class/package shadow with reviewed alias.

All fixtures are novel JDK-only examples, not original v311 recovered code.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.standalone_source_parity import (
    StandaloneSourceParityError, verify_standalone_sources,
)

SOURCES={
 "rs/k/c.java": """package rs.k;
public class c {
 private final int[] array;
 public c(){array=new int[8];}
 public void set(int i,int value){array[i]=value;}
 public int get(int i){return array[i];}
}
""",
 "rs/k/c/b.java": """package rs.k.c;
public final class b {
 private static final int[] a=new int[6];
 public b(){}
 public static int[] fill(int p,int q){
  a[0]=p-q; a[1]=p+q;
  a[2]=q-p; a[3]=p*p;
  a[4]=q*q; a[5]=p^q;
  return a;
 }
}
""",
}
ALIAS={"rs/k/c.class":"rs/k/RecoveredSyntheticBufferV311.class"}

def digest(raw:bytes)->str:
 return hashlib.sha256(raw).hexdigest()

@unittest.skipUnless(
 all(shutil.which(t) for t in ("javac","javap","java")),
 "Requires JDK9+")
class SyntheticClassPackageShadowParity(unittest.TestCase):
 def fixture(self,root:Path):
  src=root/"src"
  for name,text in SOURCES.items():
   path=src/name
   path.parent.mkdir(parents=True,exist_ok=True)
   path.write_text(text,encoding="utf-8")
  original_classes=[]
  for index,name in enumerate(sorted(SOURCES)):
   classes=root/("original-"+str(index));classes.mkdir()
   proc=subprocess.run([
    "javac","--release","9","-proc:none","-g:none",
    "-classpath",str(root/"empty-classpath"),
    "-sourcepath",str(root/"empty-sourcepath"),
    "-d",str(classes),str(src/name)
   ],capture_output=True,text=True,timeout=45)
   self.assertEqual(proc.returncode,0,proc.stderr)
   original_classes.extend(classes.rglob("*.class"))
  archive=root/"synthetic-original.jar"
  # Merge two independently compiled original-only fixtures into one jar.
  with zipfile.ZipFile(archive,"w") as out:
   for index,name in enumerate(sorted(SOURCES)):
    file=root/("original-"+str(index))/name.replace(".java",".class")
    self.assertTrue(file.is_file())
    out.writestr(name.replace(".java",".class"),file.read_bytes())
  with zipfile.ZipFile(archive) as z:
   pins={entry:digest(z.read(entry)) for entry in z.namelist()}
  self.assertEqual(len(pins),2)
  return src,archive,pins

 def test_exact_two_original_classes_rebuilt_with_inverse_jvm_alias(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory)
   src,jar,pins=self.fixture(root)
   report=verify_standalone_sources(
    jar,src,root/"rebuilt",
    original_sha256=digest(jar.read_bytes()),class_sha256=pins,
    compile_aliases=ALIAS,
   )
   self.assertTrue(report["all_passed"])
   self.assertEqual(report["total_classes"],2)
   self.assertFalse(report["original_game_binary_on_compile_classpath"])
   self.assertEqual(
    report["explicit_original_project_dependency_closure"][
     "source_project_dependency_edges"],0)
   self.assertTrue(
    (root/"rebuilt"/"restored-classfiles"/"rs/k/c.class").is_file())
   self.assertTrue(
    (root/"rebuilt"/"restored-classfiles"/"rs/k/c/b.class").is_file())

 def test_unmapped_class_package_collision_rejected(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory)
   src,jar,pins=self.fixture(root)
   with self.assertRaisesRegex(
    StandaloneSourceParityError,"COMPILE_ALIAS_CLASS_PACKAGE_COLLISION_REMAINS"
   ):
    verify_standalone_sources(
     jar,src,root/"refused",
     original_sha256=digest(jar.read_bytes()),class_sha256=pins)

 def test_changed_packed_geometry_rejected(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory)
   src,jar,pins=self.fixture(root)
   file=src/"rs/k/c/b.java"
   file.write_text(file.read_text(encoding="utf-8").replace(
    "a[1]=p+q;","a[1]=p-q;"),encoding="utf-8")
   with self.assertRaisesRegex(
    StandaloneSourceParityError,
    "ORDERED_JVM_INSTRUCTIONS_OR_DECLARATIONS_MISMATCH"
   ):
    verify_standalone_sources(
     jar,src,root/"refused",
     original_sha256=digest(jar.read_bytes()),class_sha256=pins,
     compile_aliases=ALIAS)

 def test_wrong_cross_package_alias_rejected(self):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory)
   src,jar,pins=self.fixture(root)
   with self.assertRaisesRegex(
    Exception,"COMPILE_ALIAS_MUST_PRESERVE_PACKAGE"
   ):
    verify_standalone_sources(
     jar,src,root/"refused",
     original_sha256=digest(jar.read_bytes()),class_sha256=pins,
     compile_aliases={"rs/k/c.class":"rs/ForeignAlias.class"})

if __name__=="__main__":
 unittest.main(verbosity=2)

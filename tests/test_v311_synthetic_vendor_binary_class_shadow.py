"""Synthetic JDK9 proof of real vendor binaries and reversible JVM package shadows.

All Java fixtures are novel toy classes written inside this test. There are
NO original game binaries, reconstructed game Java or vendor binary assets.
"""
from __future__ import annotations
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import tempfile
import unittest
import zipfile

MAP = """package sample_vendor.f.b;
import java.util.HashMap;
public class cc<V> {
  public static class Entry {
    public final int key;
    public Entry(int key){this.key=key;}
  }
  private final HashMap<Integer,V> data=new HashMap<Integer,V>();
  public cc(){}
  public V a(int key,V value){return data.put(key,value);}
  public V b(int key){return data.get(key);}
  public int f(){return data.size();}
}
"""
SHADOW = """package sample_vendor;
public interface f { boolean enabled(); }
"""
GAME = """package sample_v311;
public final class Registry {
  public static final int[] KEYS={7,12,31,55};
  public sample_vendor.f.b.cc<Boolean> values=new sample_vendor.f.b.cc<Boolean>();
  public Registry(){for(int key:KEYS)values.a(key,Boolean.TRUE);}
  public boolean contains(int key){return Boolean.TRUE.equals(values.b(key));}
  public int size(){return values.f();}
  public int nestedKey(){return new sample_vendor.f.b.cc.Entry(41).key;}
}
"""
PROBE = """import sample_v311.Registry;
public class ToyVendorProbe {
 public static void main(String[] ignored){
  Registry item=new Registry();
  for(int key:new int[]{-1,0,7,12,31,55,56,Integer.MAX_VALUE})
   System.out.println(key+":"+item.contains(key));
  System.out.println("SIZE="+item.size());
  System.out.println("NESTED="+item.nestedKey());
 }
}
"""
OLD="sample_vendor/f/b/cc"
ALIAS="sample_vendor/ToyRecoveredMapV311"


def rewrite_constants(blob:bytes,old:str,new:str):
    if blob[:4]!=bytes.fromhex("cafebabe"):
        raise ValueError("NOT_A_CLASSFILE")
    size=struct.unpack_from(">H",blob,8)[0]
    pos=10;index=1;changed=0;out=bytearray(blob[:10])
    while index<size:
        tag=blob[pos];out.append(tag);pos+=1
        if tag==1:
            n=struct.unpack_from(">H",blob,pos)[0];pos+=2
            value=blob[pos:pos+n];pos+=n
            revised=value.replace(old.encode(),new.encode())
            changed+=int(value!=revised)
            out.extend(struct.pack(">H",len(revised)));out.extend(revised)
        elif tag in (3,4):
            out.extend(blob[pos:pos+4]);pos+=4
        elif tag in (5,6):
            out.extend(blob[pos:pos+8]);pos+=8;index+=1
        elif tag in (7,8,16,19,20):
            out.extend(blob[pos:pos+2]);pos+=2
        elif tag in (9,10,11,12,17,18):
            out.extend(blob[pos:pos+4]);pos+=4
        elif tag==15:
            out.extend(blob[pos:pos+3]);pos+=3
        else:
            raise ValueError("UNSUPPORTED_CONSTANT_POOL_TAG")
        index+=1
    out.extend(blob[pos:])
    return bytes(out),changed


def run(args):
    p=subprocess.run(args,capture_output=True,text=True,timeout=60)
    if p.returncode:
        raise RuntimeError("JDK_COMMAND_FAILED "+p.stderr[-1400:])
    return p.stdout


def symbolic(directory,name):
    text=run(["javap","-c","-p","-s","-classpath",str(directory),name])
    return re.sub(r"#\d+(?=\s|[;,])","#CP",text)


@unittest.skipUnless(
    all(shutil.which(x) for x in ("javac","javap","java")),
    "JDK9-capable tools required",
)
class SyntheticVendorBinaryAliasTests(unittest.TestCase):
    def fixture(self,root:Path):
        sources=root/"sources"
        for name,body in {
            "sample_vendor/f/b/cc.java":MAP,
            "sample_vendor/f.java":SHADOW,
            "sample_v311/Registry.java":GAME,
        }.items():
            file=sources/name
            file.parent.mkdir(parents=True,exist_ok=True)
            file.write_text(body,encoding="utf-8")
        map_classes=root/"map-classes";map_classes.mkdir()
        run(["javac","--release","9","-proc:none","-g:none","-d",
             str(map_classes),str(sources/"sample_vendor/f/b/cc.java")])
        shadow_classes=root/"shadow-classes";shadow_classes.mkdir()
        run(["javac","--release","9","-proc:none","-g:none","-d",
             str(shadow_classes),str(sources/"sample_vendor/f.java")])
        game_classes=root/"game-classes";game_classes.mkdir()
        # Build genuine owner class against original map binary ONLY; the
        # shadow-name peer joins the final JVM JAR after owner compilation.
        run(["javac","--release","9","-proc:none","-g:none",
             "-classpath",str(map_classes),"-sourcepath",str(root/"empty-sp"),
             "-d",str(game_classes),str(sources/"sample_v311/Registry.java")])
        original=root/"toy-original.jar"
        vendor=root/"toy-original-vendor-only.jar"
        with zipfile.ZipFile(original,"w") as target,zipfile.ZipFile(vendor,"w") as only:
            for folder in (map_classes,shadow_classes,game_classes):
                for file in sorted(folder.rglob("*.class")):
                    name=file.relative_to(folder).as_posix()
                    target.writestr(name,file.read_bytes())
                    if folder!=game_classes:
                        only.writestr(name,file.read_bytes())
        aliasjar=root/"toy-vendor-aliased-only.jar"
        with zipfile.ZipFile(aliasjar,"w") as aliasout:
            for file in sorted(shadow_classes.rglob("*.class")):
                aliasout.writestr(file.relative_to(shadow_classes).as_posix(),
                                  file.read_bytes())
            for file in sorted(map_classes.rglob("*.class")):
                name=file.relative_to(map_classes).as_posix()
                renamed,count=rewrite_constants(file.read_bytes(),OLD,ALIAS)
                self.assertGreater(count,0)
                aliasout.writestr(name.replace(OLD,ALIAS),renamed)
        with zipfile.ZipFile(aliasjar) as z:
            entries=z.namelist()
            self.assertEqual(len(entries),3)
            self.assertIn(ALIAS+".class",entries)
            self.assertIn(ALIAS+"$Entry.class",entries)
            self.assertNotIn(OLD+".class",entries)
            self.assertFalse(any(x.startswith("sample_v311/") for x in entries))
        return sources,original,vendor,aliasjar

    def rebuild(self,root:Path,aliasjar:Path,game_source:str=GAME):
        stage=root/"stage/sample_v311/Registry.java"
        stage.parent.mkdir(parents=True,exist_ok=True)
        staged=game_source.replace("sample_vendor.f.b.cc",
                                   "sample_vendor.ToyRecoveredMapV311")
        self.assertNotEqual(staged,game_source)
        stage.write_text(staged,encoding="utf-8")
        compiled=root/"compiled"
        compiled.mkdir()
        run(["javac","--release","9","-proc:none","-g:none",
             "-classpath",str(aliasjar),"-sourcepath",str(root/"empty-sp"),
             "-d",str(compiled),str(stage)])
        restored=root/"restored"
        target=restored/"sample_v311/Registry.class"
        target.parent.mkdir(parents=True,exist_ok=True)
        remapped,count=rewrite_constants(
            (compiled/"sample_v311/Registry.class").read_bytes(),ALIAS,OLD)
        self.assertGreater(count,0)
        target.write_bytes(remapped)
        return restored

    def test_exact_source_bytecode_and_toy_runtime_against_real_vendor_binaries(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            _,original,vendor,aliasjar=self.fixture(root)
            restored=self.rebuild(root,aliasjar)
            self.assertEqual(symbolic(original,"sample_v311.Registry"),
                             symbolic(restored,"sample_v311.Registry"))
            probe=root/"ToyVendorProbe.java"
            probe.write_text(PROBE,encoding="utf-8")
            run(["javac","--release","9","-classpath",str(original),
                 "-d",str(root),str(probe)])
            a=run(["java","-cp",str(root)+os.pathsep+str(original),"ToyVendorProbe"])
            b=run(["java","-cp",str(root)+os.pathsep+str(restored)+os.pathsep+
                   str(vendor),"ToyVendorProbe"])
            self.assertEqual(a,b)
            self.assertEqual(len(a.splitlines()),10)

    def test_changed_method_cannot_match_original_bytecode(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            _,original,_,aliasjar=self.fixture(root)
            mutation=GAME.replace("return values.f();","return values.f()+1;")
            self.assertNotEqual(mutation,GAME)
            rebuilt=self.rebuild(root,aliasjar,mutation)
            self.assertNotEqual(symbolic(original,"sample_v311.Registry"),
                                symbolic(rebuilt,"sample_v311.Registry"))

    def test_nested_vendor_binary_is_required_not_stubbed(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            _,_,_,aliasjar=self.fixture(root)
            broken=root/"vendor-incomplete.jar"
            with zipfile.ZipFile(aliasjar) as z,zipfile.ZipFile(broken,"w") as out:
                for name in z.namelist():
                    if name==ALIAS+"$Entry.class":continue
                    out.writestr(name,z.read(name))
            with self.assertRaises(RuntimeError):
                self.rebuild(root,broken)


if __name__=="__main__":
    unittest.main(verbosity=2)

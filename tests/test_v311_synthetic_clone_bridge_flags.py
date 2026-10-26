"""Synthetic-only Java9 test for copied JVM clone-bridge access flag identity.

No original v311 source, game binaries, game data or private source archive.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest

TOY = """
package toy.vector;
public final class Point3 {
 private int x,y,z;
 public Point3(int x,int y,int z){this.x=x;this.y=y;this.z=z;}
 public Point3 copy(){return new Point3(x,y,z);}
 @Override public Object clone(){return copy();}
 public Point3 add(Point3 that){
  this.x+=that.x;this.y+=that.y;this.z+=that.z;return this;
 }
 public String toString(){return "P("+x+","+y+","+z+")";}
}
"""
PROBE = """
public final class ToyPointProbe {
 public static void main(String[] args)throws Exception{
  Class<?> owner=Class.forName("toy.vector.Point3");
  Object p=owner.getConstructor(int.class,int.class,int.class)
    .newInstance(Integer.MIN_VALUE,0,Integer.MAX_VALUE);
  System.out.println("OWNER:"+owner.getName());
  System.out.println("ORIGINAL:"+p);
  java.lang.reflect.Method clone=owner.getDeclaredMethod("clone");
  System.out.println("SYNTHETIC:"+clone.isSynthetic());
  System.out.println("COPY:"+clone.invoke(p));
  System.out.println("DISTINCT:"+(clone.invoke(p)!=p));
 }
}
"""


def restore_flag(binary: bytes, target: str, descriptor: str) -> bytes:
    if binary[:8] != bytes.fromhex("cafebabe00000035"):
        raise ValueError("NOT_JAVA9_BINARY")
    get16=lambda p:struct.unpack_from(">H",binary,p)[0]
    get32=lambda p:struct.unpack_from(">I",binary,p)[0]
    cp = {}
    idx = 1
    end = get16(8)
    pos = 10
    while idx < end:
        tag = binary[pos]
        pos += 1
        if tag == 1:
            size = get16(pos)
            pos += 2
            cp[idx] = binary[pos:pos+size].decode("utf-8")
            pos += size
        elif tag in (3,4):
            pos += 4
        elif tag in (5,6):
            pos += 8
            idx += 1
        elif tag in (7,8,16,19,20):
            pos += 2
        elif tag in (9,10,11,12,17,18):
            pos += 4
        elif tag == 15:
            pos += 3
        else:
            raise ValueError("INVALID_CONSTANT_POOL_TAG")
        idx += 1
    result=bytearray(binary)
    pos += 6
    interfaces = get16(pos)
    pos += 2 + 2*interfaces
    def skip_member(at):
        count=get16(at+6)
        at+=8
        for _ in range(count):
            at+=6+get32(at+2)
        return at
    fields=get16(pos)
    pos+=2
    for _ in range(fields):
        pos=skip_member(pos)
    methods=get16(pos)
    pos+=2
    changed=0
    for _ in range(methods):
        flags=get16(pos)
        name=cp.get(get16(pos+2))
        desc=cp.get(get16(pos+4))
        if (name,desc)==(target,descriptor):
            if flags!=0x0001:
                raise ValueError("BRIDGE_ACCESS_NOT_REVIEWED")
            struct.pack_into(">H",result,pos,0x1001)
            changed+=1
        pos=skip_member(pos)
    if changed!=1:
        raise ValueError("EXACT_BRIDGE_METHOD_NOT_FOUND")
    return bytes(result)


def run(args):
    p=subprocess.run(args,capture_output=True,text=True,timeout=45)
    if p.returncode:
        raise AssertionError(p.stderr[-1600:])
    return p.stdout


@unittest.skipUnless(all(shutil.which(x) for x in ("java","javac","javap")),
                     "Java9-capable JDK required")
class SyntheticCopyOnlyCloneBridge(unittest.TestCase):
    def fixture(self,root:Path):
        path=root/"toy/vector/Point3.java"
        path.parent.mkdir(parents=True)
        path.write_text(TOY,encoding="utf-8")
        before=root/"before"
        before.mkdir()
        run(["javac","--release","9","-proc:none","-g:none","-d",str(before),str(path)])
        return before,(before/"toy/vector/Point3.class").read_bytes()

    def test_only_synthetic_bridge_flag_changes_no_code_and_behavior_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            before,binary=self.fixture(root)
            restored=restore_flag(binary,"clone","()Ljava/lang/Object;")
            self.assertNotEqual(restored,binary)
            after=root/"after/toy/vector/Point3.class"
            after.parent.mkdir(parents=True)
            after.write_bytes(restored)
            self.assertEqual(len(restored),len(binary))
            original_disassembly=run([
                "javap","-c","-p","-s","-classpath",str(before),"toy.vector.Point3"
            ])
            rebuilt_disassembly=run([
                "javap","-c","-p","-s","-classpath",str(root/"after"),
                "toy.vector.Point3"
            ])
            self.assertEqual(original_disassembly,rebuilt_disassembly)
            verbose=run(["javap","-v","-p","-classpath",str(root/"after"),
                         "toy.vector.Point3"])
            self.assertIn("flags: (0x1001) ACC_PUBLIC, ACC_SYNTHETIC",
                          verbose.split("public java.lang.Object clone();",1)[1])
            probe=root/"ToyPointProbe.java"
            probe.write_text(PROBE,encoding="utf-8")
            run(["javac","--release","9","-d",str(root),str(probe)])
            def transcript(classes):
                return run(["java","-cp",str(root)+os.pathsep+str(classes),"ToyPointProbe"])
            a=transcript(before)
            b=transcript(root/"after")
            self.assertIn("SYNTHETIC:false",a)
            self.assertEqual(b,a.replace("SYNTHETIC:false","SYNTHETIC:true"))
            self.assertEqual(len(a.splitlines()),5)

    def test_unexpected_method_and_corrupt_bytes_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            _,binary=self.fixture(Path(tmp))
            with self.assertRaisesRegex(ValueError,"EXACT_BRIDGE_METHOD_NOT_FOUND"):
                restore_flag(binary,"notCloned","()Ljava/lang/Object;")
            with self.assertRaisesRegex(ValueError,"NOT_JAVA9_BINARY"):
                restore_flag(b"invalid","clone","()Ljava/lang/Object;")
            already=restore_flag(binary,"clone","()Ljava/lang/Object;")
            with self.assertRaisesRegex(ValueError,"BRIDGE_ACCESS_NOT_REVIEWED"):
                restore_flag(already,"clone","()Ljava/lang/Object;")


if __name__=="__main__":
    unittest.main(verbosity=2)

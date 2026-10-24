"""Synthetic-only Java9 class/package alias source integration regression.

Fixtures below are invented toy Java; no recovered game source/binaries/assets.
"""
from pathlib import Path
import hashlib
import shutil
import struct
import subprocess
import tempfile
import unittest

def run(args):
    p=subprocess.run([str(v) for v in args], capture_output=True, text=True, timeout=60)
    if p.returncode:
        raise AssertionError(p.stderr[-1500:])
    return p.stdout

def restore(blob):
    assert blob[:4]==bytes.fromhex("cafebabe")
    out=bytearray(blob[:10]); pos=10; idx=1; changes=0
    count=struct.unpack_from(">H",blob,8)[0]
    while idx<count:
        tag=blob[pos];pos+=1;out.append(tag)
        if tag==1:
            n=struct.unpack_from(">H",blob,pos)[0];pos+=2
            raw=blob[pos:pos+n];pos+=n
            changed=raw.replace(b"toy/RecoveredNode",b"toy/node")
            changes+=(changed!=raw)
            out.extend(struct.pack(">H",len(changed)));out.extend(changed)
        elif tag in (3,4,9,10,11,12,17,18):
            out.extend(blob[pos:pos+4]);pos+=4
        elif tag in (5,6):
            out.extend(blob[pos:pos+8]);pos+=8;idx+=1
        elif tag in (7,8,16,19,20):
            out.extend(blob[pos:pos+2]);pos+=2
        elif tag==15:
            out.extend(blob[pos:pos+3]);pos+=3
        else:
            raise AssertionError("unexpected constant pool tag")
        idx+=1
    out.extend(blob[pos:])
    assert changes>0
    return bytes(out)

def build(root, altered=False, include_node=True):
    src=root/"src";(src/"toy/node").mkdir(parents=True)
    (src/"toy/Base.java").write_text(
        "package toy; public class Base { public long stamp; }\n",encoding="utf-8")
    (src/"toy/node/Widget.java").write_text(
        "package toy.node; public class Widget { public int value(){ return 42; } }\n",
        encoding="utf-8")
    if include_node:
        choice="null" if altered else "this.after"
        (src/"toy/RecoveredNode.java").write_text(
            "package toy; public class RecoveredNode extends Base { "
            "public RecoveredNode next, after; "
            "public final void detach(){ if(this.after != null) this.next = "
            +choice+"; } }\n",encoding="utf-8")
    out=root/"classes";out.mkdir()
    cp=root/"empty-classpath";cp.mkdir()
    sp=root/"empty-sourcepath";sp.mkdir()
    run(["javac","--release","9","-g:none","-proc:none",
         "-classpath",cp,"-sourcepath",sp,"-d",out,
         *sorted(src.rglob("*.java"))])
    recovered=root/"restored";recovered.mkdir()
    for f in out.rglob("*.class"):
        name=f.relative_to(out).as_posix()
        new_name="toy/node.class" if name=="toy/RecoveredNode.class" else name
        dst=recovered/new_name;dst.parent.mkdir(parents=True,exist_ok=True)
        dst.write_bytes(restore(f.read_bytes()) if name!=new_name else f.read_bytes())
    return recovered

@unittest.skipUnless(all(shutil.which(x) for x in ("java","javac","javap")),
                     "JDK with Java9 support required")
class SyntheticAliasIntegration(unittest.TestCase):
    def test_added_original_identity_preserves_earlier_class_hashes(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            baseline=build(root/"baseline",include_node=False)
            first=build(root/"first")
            again=build(root/"again")
            names={p.relative_to(first).as_posix() for p in first.rglob("*.class")}
            self.assertEqual(names,{"toy/Base.class","toy/node/Widget.class","toy/node.class"})
            for name in ("toy/Base.class","toy/node/Widget.class"):
                self.assertEqual((baseline/name).read_bytes(),(first/name).read_bytes())
                self.assertEqual((first/name).read_bytes(),(again/name).read_bytes())
            self.assertEqual((first/"toy/node.class").read_bytes(),
                             (again/"toy/node.class").read_bytes())
            self.assertEqual((first/"toy/node.class").read_bytes()[:8],
                             bytes.fromhex("cafebabe00000035"))
            javap=run(["javap","-p","-s","-c","-classpath",first,"toy.node"])
            self.assertIn("toy.node next",javap)
            self.assertIn("toy.node after",javap)
            self.assertNotIn("RecoveredNode",javap)
            self.assertIn("detach",javap)

    def test_repinned_real_algorithm_mutation_must_not_be_accepted(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            reference=build(root/"reference")
            altered=build(root/"altered",altered=True)
            original_source=(root/"reference/src/toy/RecoveredNode.java").read_bytes()
            changed_source=(root/"altered/src/toy/RecoveredNode.java").read_bytes()
            original_class=(reference/"toy/node.class").read_bytes()
            changed_class=(altered/"toy/node.class").read_bytes()
            # Both pairs have internally coherent SHA hashes; only original
            # JVM instruction parity determines whether the change is accepted.
            self.assertNotEqual(hashlib.sha256(original_source).digest(),
                                hashlib.sha256(changed_source).digest())
            self.assertNotEqual(hashlib.sha256(original_class).digest(),
                                hashlib.sha256(changed_class).digest())
            before=run(["javap","-p","-s","-c","-classpath",reference,"toy.node"])
            after=run(["javap","-p","-s","-c","-classpath",altered,"toy.node"])
            self.assertNotEqual(before,after)
            for unchanged in ("toy/Base.class","toy/node/Widget.class"):
                self.assertEqual((reference/unchanged).read_bytes(),
                                 (altered/unchanged).read_bytes())

if __name__=="__main__":
    unittest.main(verbosity=2)

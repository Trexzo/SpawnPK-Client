"""JDK-only synthetic scene record/node source-island regression.

Uses independent toy classes, never proprietary game code or original client binaries.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile
import os

from spk_recovery.standalone_source_parity import (
    StandaloneSourceParityError, verify_standalone_sources,
)
from spk_recovery.source_dependency_closure import (
    SourceClosureError, require_selected_source_closure,
)


SOURCES = {
    "rs/example/AnchorNode.java": """
package rs.example;
public class AnchorNode {
 public AnchorNode next;
 public int id;
 public void detach() { next=null; }
}
""",
    "rs/example/QuadRecord.java": """
package rs.example;
public final class QuadRecord {
 public final int[] values;
 public QuadRecord(int slots) { values=new int[slots * 4]; }
 public void set(int slot,int value) { values[slot * 4 + 2]=value; }
 public int get(int slot) { return values[slot * 4 + 2]; }
 public void add(int slot,int delta) { values[slot * 4 + 2]+=delta; }
}
""",
    "rs/example/TileSlot.java": """
package rs.example;
public final class TileSlot extends AnchorNode {
 public QuadRecord records;
 public TileSlot(int slots) { records=new QuadRecord(slots); }
 public int sample(int slot) { return records.get(slot); }
}
""",
}

PROBE = """
import rs.example.*;
public final class ToySceneProbe {
 public static void main(String[] args) {
  TileSlot first=new TileSlot(3),second=new TileSlot(2);
  first.id=7;second.id=9;first.next=second;
  System.out.println("links:"+first.id+":"+first.next.id);
  first.records.set(1,30);first.records.add(1,12);
  System.out.println("records:"+first.sample(1)+":"+first.records.values.length);
  first.detach();
  System.out.println("detached:"+(first.next==null));
  try {first.records.set(3,1);System.out.println("no-boundary");}
  catch(Throwable t){System.out.println("boundary:"+t.getClass().getSimpleName());}
 }
}
"""


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@unittest.skipUnless(
    all(shutil.which(x) for x in ("javac", "javap", "java")),
    "Requires Java9 capable JDK",
)
class ToySceneIslandSourceTests(unittest.TestCase):
    def fixture(self, root: Path):
        source=root/"source"
        for name, code in SOURCES.items():
            target=source/name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(code, encoding="utf-8")
        compiled=root/"first-classes"
        compiled.mkdir()
        result=subprocess.run([
            "javac","--release","9","-proc:none","-g:none",
            "-encoding","UTF-8","-classpath",str(root/"empty-cp"),
            "-sourcepath",str(root/"empty-sp"),"-d",str(compiled),
            *[str(source/name) for name in sorted(SOURCES)],
        ], capture_output=True,text=True,timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        jar=root/"toy-original.jar"
        with zipfile.ZipFile(jar,"w") as archive:
            for classfile in sorted(compiled.rglob("*.class")):
                archive.writestr(classfile.relative_to(compiled).as_posix(),
                                 classfile.read_bytes())
        with zipfile.ZipFile(jar) as archive:
            original={name:sha(archive.read(name)) for name in archive.namelist()}
        self.assertEqual(len(original),3)
        return source,jar,original

    def test_connected_sources_compile_match_and_run(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            source,jar,pins=self.fixture(root)
            report=verify_standalone_sources(
                jar,source,root/"rebuilt",
                original_sha256=sha(jar.read_bytes()),class_sha256=pins,
            )
            self.assertTrue(report["all_passed"])
            self.assertEqual(report["total_classes"],3)
            self.assertFalse(report["original_game_binary_on_compile_classpath"])
            closure=report["explicit_original_project_dependency_closure"]
            self.assertGreaterEqual(closure["source_project_dependency_edges"],2)
            probe=root/"ToySceneProbe.java"
            probe.write_text(PROBE,encoding="utf-8")
            build=subprocess.run([
                "javac","--release","9","-cp",str(jar),
                "-d",str(root),str(probe)
            ],capture_output=True,text=True,timeout=45)
            self.assertEqual(build.returncode,0,build.stderr)
            outputs=[]
            for cp in (jar,root/"rebuilt"/"classes"):
                check=subprocess.run([
                    "java","-cp",str(root)+os.pathsep+str(cp),"ToySceneProbe"
                ],capture_output=True,text=True,timeout=45)
                self.assertEqual(check.returncode,0,check.stderr)
                outputs.append(check.stdout)
            self.assertEqual(outputs[0],outputs[1])
            self.assertEqual(len(outputs[0].splitlines()),4)
            self.assertIn("records:42:12",outputs[0])

    def test_missing_declared_dependencies_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            _,jar,_=self.fixture(root)
            with zipfile.ZipFile(jar) as archive:
                with self.assertRaisesRegex(
                    SourceClosureError,"PROJECT_SOURCE_DEPENDENCY_OUTSIDE_SELECTION"
                ):
                    require_selected_source_closure(archive,{
                        "rs/example/AnchorNode.class",
                        "rs/example/TileSlot.class",
                    })

    def test_wrong_slot_multiplier_refused_before_acceptance(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            source,jar,pins=self.fixture(root)
            item=source/"rs/example/QuadRecord.java"
            item.write_text(item.read_text(encoding="utf-8").replace(
                "slot * 4 + 2","slot * 4 + 1"
            ),encoding="utf-8")
            with self.assertRaisesRegex(
                StandaloneSourceParityError,
                "ORDERED_JVM_INSTRUCTIONS_OR_DECLARATIONS_MISMATCH",
            ):
                verify_standalone_sources(
                    jar,source,root/"rejected",
                    original_sha256=sha(jar.read_bytes()),class_sha256=pins,
                )
            self.assertFalse((root/"rejected"/"SOURCE-REBUILD-VERIFY.json").exists())


if __name__=="__main__":
    unittest.main(verbosity=2)

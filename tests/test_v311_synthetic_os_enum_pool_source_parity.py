"""Novel synthetic-only Java9 OS-enum and bounded record-pool source parity.

No recovered original v311 Java, real vendor binary, game classfile,
original-game constant, account information or private probe transcript.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.standalone_source_parity import (
    StandaloneSourceParityError, verify_standalone_sources,
)

SOURCES = {
    "rs/synthetic100/HostFamily.java": """
package rs.synthetic100;
public enum HostFamily {
  Cedar, Juniper, Willow, Other;
  private static final HostFamily CURRENT;
  public static HostFamily selected(){return CURRENT;}
  static {
    String text=System.getProperty("synthetic.host","generic").toLowerCase();
    if(text.contains("cedar")||text.contains("ced"))CURRENT=Cedar;
    else if(text.contains("juniper"))CURRENT=Juniper;
    else if(text.contains("willow"))CURRENT=Willow;
    else CURRENT=Other;
  }
}
""",
    "rs/synthetic100/TicketPool.java": """
package rs.synthetic100;
import java.util.HashMap;
public final class TicketPool {
  private static int cursor;
  private static final int LIMIT=37;
  private static final HashMap<Integer,TicketPool> registered=new HashMap<>();
  private static final TicketPool[] items=new TicketPool[LIMIT];
  private int first,second;
  public static void reset(){cursor=0;registered.clear();}
  public static void register(int key,TicketPool item){registered.put(key,item);}
  public static TicketPool lookup(int key){return registered.get(key);}
  public static TicketPool next(){return items[cursor++];}
  public TicketPool first(int value){first=value;return this;}
  public TicketPool second(int value){second=value;return this;}
  public int first(){return first;}
  public int second(){return second;}
  static {
    for(int i=0;i<LIMIT;i++)items[i]=new TicketPool();
  }
}
""",
}

PROBE = """
import rs.synthetic100.*;
public final class ToyR100Runtime {
  public static void main(String[] args) {
    int count=0;
    for(HostFamily family:HostFamily.values()) {
      System.out.println("HOST:"+family.name()+":"+family.ordinal()+":"+
        (HostFamily.valueOf(family.name())==family));
      count++;
    }
    System.out.println("ACTIVE:"+HostFamily.selected().name());count++;
    TicketPool.reset();
    int[] keys={Integer.MIN_VALUE,-3,-1,0,1,3,37,100,Integer.MAX_VALUE};
    for(int key:keys) {
      TicketPool record=new TicketPool().first(key).second(~key);
      TicketPool.register(key,record);
      System.out.println("TICKET:"+key+":"+
        (TicketPool.lookup(key)==record)+":"+
        record.first()+":"+record.second());count++;
    }
    TicketPool a=TicketPool.next(),b=TicketPool.next();
    System.out.println("DISTINCT:"+(a!=b));count++;
    TicketPool.reset();
    System.out.println("RESET:"+(TicketPool.next()==a)+":"+
      (TicketPool.lookup(keys[0])==null));count++;
    if(count!=16)throw new AssertionError("WRONG_SYNTHETIC_CASE_COUNT_"+count);
  }
}
"""


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def run(command):
    p = subprocess.run(command, capture_output=True, text=True, timeout=55)
    if p.returncode:
        raise RuntimeError(p.stderr[-1600:])
    return p.stdout


@unittest.skipUnless(
    all(shutil.which(name) for name in ("java", "javac", "javap")),
    "A Java9-compatible JDK is required",
)
class R100SyntheticOSPoolTests(unittest.TestCase):
    def fixture(self, root: Path):
        src = root / "source"
        for name, contents in SOURCES.items():
            path = src / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(contents, encoding="utf-8")
        classes = root / "toy-original"
        classes.mkdir()
        run(["javac", "--release", "9", "-proc:none", "-g:none",
             "-classpath", str(root / "empty-classpath"),
             "-sourcepath", str(root / "empty-sourcepath"),
             "-d", str(classes), *[str(src / x) for x in sorted(SOURCES)]])
        jar = root / "toy-original.jar"
        with zipfile.ZipFile(jar, "w") as output:
            for f in sorted(classes.rglob("*.class")):
                output.writestr(f.relative_to(classes).as_posix(), f.read_bytes())
        with zipfile.ZipFile(jar) as z:
            pins = {name: sha(z.read(name)) for name in z.namelist()}
        self.assertEqual(len(pins), 2)
        return src, jar, pins

    def test_two_source_classes_six_platform_scenarios_and_pool_parity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, jar, pins = self.fixture(root)
            result = verify_standalone_sources(
                jar, source, root / "rebuilt",
                original_sha256=sha(jar.read_bytes()), class_sha256=pins,
            )
            self.assertTrue(result["all_passed"])
            self.assertEqual(result["total_classes"], 2)
            self.assertFalse(result["original_game_binary_on_compile_classpath"])
            self.assertEqual(
                result["explicit_original_project_dependency_closure"][
                    "unresolved_project_dependency_edges"
                ], 0,
            )
            probe = root / "ToyR100Runtime.java"
            probe.write_text(PROBE, encoding="utf-8")
            run(["javac", "--release", "9", "-cp", str(jar),
                 "-d", str(root), str(probe)])
            names = ("Cedar OS", "ced 9", "Juniper", "willow",
                     "generic", "OTHER")
            observed = []
            for platform in names:
                transcripts = []
                for binary in (jar, root / "rebuilt" / "classes"):
                    transcripts.append(run([
                        "java", "-Dsynthetic.host=" + platform,
                        "-cp", str(root) + os.pathsep + str(binary),
                        "ToyR100Runtime",
                    ]))
                self.assertEqual(transcripts[0], transcripts[1])
                self.assertEqual(len(transcripts[0].splitlines()), 16)
                observed.append(next(
                    x for x in transcripts[0].splitlines()
                    if x.startswith("ACTIVE:")
                ))
            self.assertEqual(len(set(observed)), 4)

    def test_changed_pool_method_refused_by_exact_original_instructions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, jar, pins = self.fixture(root)
            f = source / "rs/synthetic100/TicketPool.java"
            original = f.read_text()
            altered = original.replace(
                "second=value;return this;", "first=value;return this;"
            )
            self.assertNotEqual(altered, original)
            f.write_text(altered, encoding="utf-8")
            with self.assertRaisesRegex(
                StandaloneSourceParityError,
                "ORDERED_JVM_INSTRUCTIONS_OR_DECLARATIONS_MISMATCH",
            ):
                verify_standalone_sources(
                    jar, source, root / "refused",
                    original_sha256=sha(jar.read_bytes()), class_sha256=pins,
                )

    def test_missing_source_and_wrong_original_jar_sha_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, jar, pins = self.fixture(root)
            with self.assertRaisesRegex(
                StandaloneSourceParityError, "WRONG_ORIGINAL_JAR",
            ):
                verify_standalone_sources(
                    jar, source, root / "wrong",
                    original_sha256="0" * 64, class_sha256=pins,
                )
            (source / "rs/synthetic100/HostFamily.java").unlink()
            with self.assertRaises(StandaloneSourceParityError):
                verify_standalone_sources(
                    jar, source, root / "missing",
                    original_sha256=sha(jar.read_bytes()), class_sha256=pins,
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)

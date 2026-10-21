"""Source-only CI: real javac rebuild parity, errors and no game JAR fallback."""
from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.standalone_source_parity import (
    StandaloneSourceParityError,
    _normalize_javap,
    require_compilable_source_namespace,
    verify_standalone_sources,
)


SYNTHETIC_SRC = {
    "rs/demo/Node.java": """
package rs.demo;
public final class Node {
    public long value;
    public Node previous;
    public Node next;
    public final void detach() {
        if (next == null) {
        } else {
            next.previous = previous;
            previous.next = next;
            previous = null;
            next = null;
        }
    }
    public Node() {}
}
""",
    "rs/demo/Failure.java": """
package rs.demo;
public final class Failure extends Exception {
    public Failure(String msg) { super(msg); }
    public Failure(Throwable cause) { super(cause); }
}
""",
    "rs/demo/Wait.java": """
package rs.demo;
public final class Wait {
    public static void pause(long millis) {
        if (millis > 0) {
            try { Thread.sleep(millis); }
            catch (InterruptedException e) { e.printStackTrace(); }
        }
    }
}
""",
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


class JavaFixture:
    def __init__(self, root: Path):
        self.root = root
        self.src = root / "source"
        self.jar = root / "synthetic-original.jar"
        self.expected = {}
        for path, body in SYNTHETIC_SRC.items():
            source = self.src / path
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text(body, encoding="utf-8")
        compiled = root / "original-classes"
        compiled.mkdir()
        out = subprocess.run(
            [
                "javac", "--release", "9", "-proc:none", "-g:none",
                "-encoding", "UTF-8", "-classpath", str(root / "empty_cp"),
                "-sourcepath", str(root / "empty_src"), "-d", str(compiled),
                *[str(self.src / name) for name in sorted(SYNTHETIC_SRC)],
            ],
            capture_output=True, text=True, timeout=45,
        )
        if out.returncode:
            raise AssertionError("fixture failed to build: " + out.stderr[:500])
        with zipfile.ZipFile(self.jar, "w") as z:
            for path in sorted(compiled.rglob("*.class")):
                rel = path.relative_to(compiled).as_posix()
                data = path.read_bytes()
                self.expected[rel] = sha(data)
                z.writestr(rel, data)
        self.jar_hash = sha(self.jar.read_bytes())


@unittest.skipUnless(shutil.which("javac") and shutil.which("javap"),
                     "Requires the same JDK preinstalled in Recovery CI")
class StandaloneSourceParityTests(unittest.TestCase):
    def test_three_actual_compilable_synthetic_classes_match(self):
        with tempfile.TemporaryDirectory() as directory:
            obj = JavaFixture(Path(directory))
            report = verify_standalone_sources(
                obj.jar, obj.src, obj.root / "accepted",
                original_sha256=obj.jar_hash,
                class_sha256=obj.expected,
            )
            self.assertTrue(report["all_passed"])
            self.assertEqual(report["total_classes"], 3)
            self.assertGreater(report["total_ordered_instructions"], 15)
            self.assertFalse(report["original_game_binary_on_compile_classpath"])
            self.assertFalse(report["complete_v311_source_recovery"])
            self.assertEqual(report["full_classfile_or_graphical_parity"], "NOT_PROVEN")
            self.assertTrue((obj.root / "accepted" / "SOURCE-REBUILD-VERIFY.json").is_file())
            # Unlike the previous verifier, this must compare original
            # exception table start/end/target and exact catch type.
            self.assertGreater(
                next(x for x in report["results"]
                     if x["class_entry"] == "rs/demo/Wait.class")[
                    "matched_exception_handler_entries"
                ], 0,
            )
            self.assertEqual(
                len(list((obj.root / "accepted" / "classes").rglob("*.class"))), 3
            )

    def test_operand_normalization_keeps_offsets_and_resolved_targets(self):
        one = """
public class rs.demo.Node {
  public rs.demo.Node();
    descriptor: ()V
    Code:
       0: aload_0
       1: invokespecial #1 // Method java/lang/Object.\"<init>\":()V
       4: return
}
"""
        two = one.replace("#1", "#123")
        self.assertEqual(_normalize_javap(one), _normalize_javap(two))
        self.assertNotEqual(_normalize_javap(one), _normalize_javap(
            one.replace("4: return", "5: return")
        ))
        self.assertNotEqual(_normalize_javap(one), _normalize_javap(
            one.replace("java/lang/Object", "java/lang/Exception")
        ))

    def test_unresolved_constant_pool_operand_refuses(self):
        example = """
public class rs.demo.Node {
  public rs.demo.Node();
    descriptor: ()V
    Code:
       0: aload_0
       1: invokespecial #34
       4: return
}
"""
        with self.assertRaisesRegex(StandaloneSourceParityError, "UNRESOLVED"):
            _normalize_javap(example)

    def test_exception_handler_symbolic_type_and_range_are_compared(self):
        example = """
public class rs.demo.Wait {
  public rs.demo.Wait();
    descriptor: ()V
    Code:
       0: aload_0
       1: invokespecial #1 // Method java/lang/Object."<init>":()V
       4: return
  public static void pause(long);
    descriptor: (J)V
    Code:
       0: lconst_0
       1: return
    Exception table:
       from    to  target type
          0    1    1   Class java/lang/InterruptedException
}
"""
        baseline = _normalize_javap(example)[0]
        self.assertIn(
            "HANDLER 0 1 1 Class java/lang/InterruptedException", baseline
        )
        self.assertNotEqual(
            baseline,
            _normalize_javap(example.replace(
                "0    1    1   Class", "0    2    1   Class"
            ))[0],
        )
        self.assertNotEqual(
            baseline,
            _normalize_javap(example.replace(
                "java/lang/InterruptedException", "java/lang/Exception"
            ))[0],
        )

    def test_malformed_exception_table_refuses(self):
        example = """
public class rs.demo.Wait {
  public static void pause();
    descriptor: ()V
    Code:
       0: return
    Exception table:
       from    to  target type
          garbage
}
"""
        with self.assertRaisesRegex(StandaloneSourceParityError, "EMPTY_EXCEPTION_TABLE"):
            _normalize_javap(example)
        with self.assertRaisesRegex(
            StandaloneSourceParityError, "MALFORMED_EXCEPTION_HANDLER_RANGE"
        ):
            _normalize_javap(example.replace(
                "          garbage",
                "          3    1    4   Class java/lang/RuntimeException",
            ))

    def test_unrenamed_class_package_collision_refused(self):
        with self.assertRaisesRegex(
            StandaloneSourceParityError, "SOURCE_CLASS_PACKAGE_COLLISION"
        ):
            require_compilable_source_namespace({
                "rs/t.class", "rs/t/f.class", "rs/t/h.class",
            })
        require_compilable_source_namespace({
            "rs/t/f.class", "rs/t/h.class",
            "rs/runelite/events/MenuOpened.class",
        })
        with self.assertRaisesRegex(StandaloneSourceParityError, "INVALID_CLASS_PATH"):
            require_compilable_source_namespace({"rs/../unsafe.class"})

    def test_wrong_original_jar_pin_refuses_before_any_output(self):
        with tempfile.TemporaryDirectory() as directory:
            obj = JavaFixture(Path(directory))
            dest = obj.root / "should-not-exist"
            with self.assertRaisesRegex(StandaloneSourceParityError, "WRONG_ORIGINAL_JAR"):
                verify_standalone_sources(
                    obj.jar, obj.src, dest,
                    original_sha256="a" * 64, class_sha256=obj.expected,
                )
            self.assertFalse(dest.exists())

    def test_wrong_class_pin_refuses_before_compile(self):
        with tempfile.TemporaryDirectory() as directory:
            obj = JavaFixture(Path(directory))
            dest = obj.root / "should-not-exist"
            bad = dict(obj.expected)
            bad["rs/demo/Node.class"] = "c" * 64
            with self.assertRaisesRegex(StandaloneSourceParityError, "WRONG_ORIGINAL_CLASS"):
                verify_standalone_sources(
                    obj.jar, obj.src, dest,
                    original_sha256=obj.jar_hash, class_sha256=bad,
                )
            self.assertFalse(dest.exists())

    def test_changed_source_body_refuses_instruction_parity(self):
        with tempfile.TemporaryDirectory() as directory:
            obj = JavaFixture(Path(directory))
            src = obj.src / "rs/demo/Node.java"
            src.write_text(src.read_text(encoding="utf-8").replace(
                "next.previous = previous;", "next.previous = this;"
            ), encoding="utf-8")
            dest = obj.root / "mismatch"
            with self.assertRaisesRegex(StandaloneSourceParityError, "INSTRUCTIONS_OR_DECLARATIONS_MISMATCH"):
                verify_standalone_sources(
                    obj.jar, obj.src, dest,
                    original_sha256=obj.jar_hash, class_sha256=obj.expected,
                )
            self.assertFalse((dest / "SOURCE-REBUILD-VERIFY.json").exists())

    def test_missing_project_source_is_fail_closed_before_write(self):
        with tempfile.TemporaryDirectory() as directory:
            obj = JavaFixture(Path(directory))
            (obj.src / "rs/demo/Node.java").unlink()
            dest = obj.root / "missing"
            with self.assertRaisesRegex(StandaloneSourceParityError, "SOURCE_FILE_MISSING"):
                verify_standalone_sources(
                    obj.jar, obj.src, dest,
                    original_sha256=obj.jar_hash, class_sha256=obj.expected,
                )
            self.assertFalse(dest.exists())

    def test_existing_result_directory_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            obj = JavaFixture(Path(directory))
            dest = obj.root / "exists"; dest.mkdir()
            sentinel = dest / "sentinel.txt"
            sentinel.write_text("unchanged", encoding="utf-8")
            with self.assertRaisesRegex(StandaloneSourceParityError, "OUTPUT_ALREADY_EXISTS"):
                verify_standalone_sources(
                    obj.jar, obj.src, dest,
                    original_sha256=obj.jar_hash, class_sha256=obj.expected,
                )
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "unchanged")

    def test_duplicate_class_names_in_original_archive_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            obj = JavaFixture(Path(directory))
            duplicated = obj.root / "duplicate.jar"
            with zipfile.ZipFile(obj.jar) as orig:
                records = [(name, orig.read(name)) for name in orig.namelist()]
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                with zipfile.ZipFile(duplicated, "w") as z:
                    for name, body in records:
                        z.writestr(name, body)
                    z.writestr(*records[0])
            dest = obj.root / "no-output"
            with self.assertRaisesRegex(StandaloneSourceParityError, "AMBIGUOUS_ORIGINAL_ZIP_ENTRIES"):
                verify_standalone_sources(
                    duplicated, obj.src, dest,
                    original_sha256=sha(duplicated.read_bytes()),
                    class_sha256=obj.expected,
                )
            self.assertFalse(dest.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)

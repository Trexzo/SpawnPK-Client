from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

from spk_recovery.source_normalization import (
    _normalize_direct_generic_factory_target_inference_casts,
)


GOOD_ASSIGNMENT = "this.subscribers = Bag.f();"
BROKEN_ASSIGNMENT = (
    "this.subscribers = (Bag<Class<?>, Subscriber>)Bag.f();"
)


def bag_source(*, generic_factory: bool = True) -> str:
    factory = (
        "public static <K,V> Bag<K,V> f() { return new Bag<>(); }"
        if generic_factory
        else "public static Bag f() { return new Bag(); }"
    )
    return "package p; public class Bag<K,V> { " + factory + " }\n"


def bus_source(*, duplicate: bool = False) -> str:
    return (
        "package p;\n"
        "public class Bus {\n"
        "  public static class Subscriber {}\n"
        "  private Bag<Class<?>, Subscriber> subscribers;\n"
        "  public Bus() {\n"
        "    " + GOOD_ASSIGNMENT + "\n"
        + ("    " + GOOD_ASSIGNMENT + "\n" if duplicate else "")
        + "  }\n"
        "}\n"
    )


@unittest.skipUnless(shutil.which("javac"), "JDK compiler required")
class GenericStaticFactoryConstructorSourceM1Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "src"
        (self.source / "p").mkdir(parents=True)
        self.bus = self.source / "p" / "Bus.java"
        self.bag = self.source / "p" / "Bag.java"
        self.bag.write_text(bag_source(), encoding="utf-8")
        self.bus.write_text(bus_source(), encoding="utf-8")
        self.original = self.bus.read_text(encoding="utf-8")
        self.jar = self.create_authority()
        self.bus.write_text(
            self.original.replace(GOOD_ASSIGNMENT, BROKEN_ASSIGNMENT),
            encoding="utf-8",
        )

    def compile(self, out):
        out.mkdir(parents=True, exist_ok=True)
        return subprocess.run(
            [
                "javac", "--release", "11", "-proc:none", "-d", str(out),
                str(self.bag), str(self.bus),
            ],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )

    def create_authority(self):
        out = self.root / "authority"
        result = self.compile(out)
        self.assertEqual(result.returncode, 0, result.stderr)
        dest = self.root / "readable.jar"
        with zipfile.ZipFile(dest, "w") as z:
            for file in out.rglob("*.class"):
                z.write(file, file.relative_to(out).as_posix())
        return dest

    def normalize(self):
        with zipfile.ZipFile(self.jar) as z:
            return _normalize_direct_generic_factory_target_inference_casts(
                source_root=self.source, path=self.bus, readable_zip=z,
            )

    def test_constructor_cast_is_removed_by_exact_field_factory_flow(self):
        before = self.compile(self.root / "broken")
        self.assertNotEqual(before.returncode, 0)
        self.assertIn("incompatible types", before.stderr)
        actions = self.normalize()
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["method_name"], "<init>")
        self.assertEqual(actions[0]["method_descriptor"], "()V")
        self.assertEqual(actions[0]["replacement_count"], 1)
        self.assertEqual(actions[0]["mode"], "direct_static_factory")
        self.assertEqual(self.bus.read_text(encoding="utf-8"), self.original)
        after = self.compile(self.root / "repaired")
        self.assertEqual(after.returncode, 0, after.stderr)
        self.assertEqual(self.normalize(), [])

    def test_non_generic_factory_signature_is_not_repaired(self):
        self.bag.write_text(bag_source(generic_factory=False), encoding="utf-8")
        self.bus.write_text(self.original, encoding="utf-8")
        self.jar = self.create_authority()
        self.bus.write_text(
            self.original.replace(GOOD_ASSIGNMENT, BROKEN_ASSIGNMENT),
            encoding="utf-8",
        )
        self.assertEqual(self.normalize(), [])
        self.assertIn(BROKEN_ASSIGNMENT, self.bus.read_text(encoding="utf-8"))

    def test_multiple_bytecode_factory_writes_for_one_cast_fail_closed(self):
        self.bus.write_text(bus_source(duplicate=True), encoding="utf-8")
        self.jar = self.create_authority()
        self.bus.write_text(
            self.original.replace(GOOD_ASSIGNMENT, BROKEN_ASSIGNMENT),
            encoding="utf-8",
        )
        self.assertEqual(self.normalize(), [])

    def test_different_factory_spelling_does_not_match_readable_bytecode(self):
        self.bus.write_text(
            self.original.replace(GOOD_ASSIGNMENT, (
                "this.subscribers = (Bag<Class<?>, Subscriber>)Bag.other();"
            )),
            encoding="utf-8",
        )
        self.assertEqual(self.normalize(), [])


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

from spk_recovery.source_normalization import (
    _normalize_shadowed_nested_static_field_owners,
    _normalize_shadowed_nested_static_method_owners,
)


GOOD_OWNER = "((outer.d.a)null)"
BROKEN_OWNER = "d.a"


def source_outer(*, shadow: bool = True) -> str:
    return (
        "package outer;\n"
        "public class d {\n"
        + ("    public static int a = 3;\n" if shadow else "")
        + "    public enum a { b, c, z }\n"
        "}\n"
    )


def good_source() -> str:
    return (
        "package test;\n"
        "import outer.d;\n"
        "class SwitchMap {\n"
        "    static final int[] map;\n"
        "    static {\n"
        "        map = new int[" + GOOD_OWNER + ".values().length];\n"
        "        try { map[" + GOOD_OWNER + ".b.ordinal()] = 1; }\n"
        "        catch (NoSuchFieldError ignored) {}\n"
        "        try { map[" + GOOD_OWNER + ".c.ordinal()] = 2; }\n"
        "        catch (NoSuchFieldError ignored) {}\n"
        "        try { map[" + GOOD_OWNER + ".z.ordinal()] = 3; }\n"
        "        catch (NoSuchFieldError ignored) {}\n"
        "    }\n"
        "}\n"
    )


@unittest.skipUnless(shutil.which("javac"), "JDK compiler required")
class ImportedOuterNestedEnumSourceM1Tests(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.root = Path(self.td.name)
        self.src = self.root / "src"
        self.classes = self.root / "classes"
        self.classes.mkdir()
        (self.src / "outer").mkdir(parents=True)
        (self.src / "test").mkdir(parents=True)
        self.outer = self.src / "outer" / "d.java"
        self.target = self.src / "test" / "SwitchMap.java"
        self.outer.write_text(source_outer(), encoding="utf-8")
        self.target.write_text(good_source(), encoding="utf-8")
        process = self.javac(self.classes)
        if process.returncode:
            raise AssertionError(process.stderr)
        self.jar = self.root / "readable.jar"
        with zipfile.ZipFile(self.jar, "w") as z:
            for file in self.classes.rglob("*.class"):
                z.write(file, file.relative_to(self.classes).as_posix())
        self.bad_source = good_source().replace(GOOD_OWNER, BROKEN_OWNER)
        self.assertEqual(self.bad_source.count(BROKEN_OWNER), 4)
        self.target.write_text(self.bad_source, encoding="utf-8")

    def javac(self, out: Path):
        out.mkdir(parents=True, exist_ok=True)
        return subprocess.run(
            [
                "javac", "--release", "11", "-proc:none",
                "-d", str(out),
                str(self.outer), str(self.target),
            ],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )

    def rewrite(self):
        with zipfile.ZipFile(self.jar) as z:
            method_actions = _normalize_shadowed_nested_static_method_owners(
                source_root=self.src, path=self.target, readable_zip=z,
            )
            field_actions = _normalize_shadowed_nested_static_field_owners(
                source_root=self.src, path=self.target, readable_zip=z,
            )
        return method_actions, field_actions

    def test_exact_imported_outer_rewrites_one_method_and_three_enum_fields(self):
        before = self.javac(self.root / "before")
        self.assertNotEqual(before.returncode, 0)
        self.assertIn("cannot be dereferenced", before.stderr)

        methods, fields = self.rewrite()
        self.assertEqual(sum(x["replacement_count"] for x in methods), 1)
        self.assertEqual(sum(x["replacement_count"] for x in fields), 3)
        normalized = self.target.read_text(encoding="utf-8")
        self.assertEqual(normalized.count(GOOD_OWNER), 4)
        self.assertNotIn(BROKEN_OWNER, normalized)

        after = self.javac(self.root / "after")
        self.assertEqual(after.returncode, 0, after.stderr)
        self.assertEqual(self.rewrite(), ([], []))

    def test_removed_explicit_import_fails_closed(self):
        self.target.write_text(
            self.bad_source.replace("import outer.d;", "import java.util.List;"),
            encoding="utf-8",
        )
        self.assertEqual(self.rewrite(), ([], []))
        self.assertIn(BROKEN_OWNER, self.target.read_text(encoding="utf-8"))

    def test_unknown_new_import_owner_fails_closed(self):
        self.target.write_text(
            self.bad_source.replace("import outer.d;", "import fake.d;"),
            encoding="utf-8",
        )
        self.assertEqual(self.rewrite(), ([], []))

    def test_field_multiplicity_mismatch_does_not_edit_fields(self):
        self.target.write_text(
            self.bad_source.replace("map[d.a.b.ordinal()] = 1;",
                                    "map[d.a.b.ordinal()] = d.a.b.ordinal();"),
            encoding="utf-8",
        )
        with zipfile.ZipFile(self.jar) as z:
            actions = _normalize_shadowed_nested_static_field_owners(
                source_root=self.src, path=self.target, readable_zip=z,
            )
        self.assertEqual(actions, [])
        self.assertEqual(self.target.read_text(encoding="utf-8").count(BROKEN_OWNER), 5)

    def test_missing_original_value_shadow_keeps_source_unchanged(self):
        other_classes = self.root / "other-classes"
        self.outer.write_text(source_outer(shadow=False), encoding="utf-8")
        self.target.write_text(good_source(), encoding="utf-8")
        result = self.javac(other_classes)
        self.assertEqual(result.returncode, 0, result.stderr)
        no_shadow_jar = self.root / "no-shadow.jar"
        with zipfile.ZipFile(no_shadow_jar, "w") as z:
            for file in other_classes.rglob("*.class"):
                z.write(file, file.relative_to(other_classes).as_posix())
        self.target.write_text(self.bad_source, encoding="utf-8")
        with zipfile.ZipFile(no_shadow_jar) as z:
            self.assertEqual(
                _normalize_shadowed_nested_static_method_owners(
                    source_root=self.src, path=self.target, readable_zip=z,
                ), [],
            )
            self.assertEqual(
                _normalize_shadowed_nested_static_field_owners(
                    source_root=self.src, path=self.target, readable_zip=z,
                ), [],
            )
        self.assertEqual(self.target.read_text(encoding="utf-8"), self.bad_source)


if __name__ == "__main__":
    unittest.main()

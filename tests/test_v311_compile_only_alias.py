"""Source-only Java9 end-to-end regression for compile-only class aliases."""
from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.standalone_source_alias import (
    StandaloneAliasError, validate_compile_aliases, rename_owned_class_source,
    ensure_no_external_alias_refs,
)
from spk_recovery.standalone_source_parity import (
    verify_standalone_sources,
)


ORIGINAL = "rs/t.class"
ALIAS = "rs/RecoveredNodeV311.class"
CHILD = "rs/t/f.class"
NODE_SOURCE = """package rs;
public class t {
    public t e;
    public t d;
    public t() {}
    public final void detach() {
        if (e == null) {
        } else {
            e.d = d;
            d.e = e;
            d = null;
            e = null;
        }
    }
}
"""
CHILD_SOURCE = """package rs.t;
public class f {
    public static final float a;
    public static final float b;
    f() { throw new Error(); }
    static {
        a = Math.ulp(1.0f);
        b = 2.0f * a;
    }
}
"""


def digest(contents: bytes) -> str:
    return hashlib.sha256(contents).hexdigest()


@unittest.skipUnless(shutil.which("javac") and shutil.which("javap"),
                     "Requires JDK in Recovery CI")
class CompileOnlyAliasTests(unittest.TestCase):
    def make_original(self, root: Path):
        src = root / "sources"
        for relative, text in [
            ("rs/t.java", NODE_SOURCE),
            ("rs/t/f.java", CHILD_SOURCE),
        ]:
            path = src / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        artifact = root / "original-fixture.jar"
        expected = {}
        with zipfile.ZipFile(artifact, "w") as output:
            for entry in (ORIGINAL, CHILD):
                relative = entry[:-6] + ".java"
                target = root / ("compile-" + str(len(expected)))
                target.mkdir()
                proc = subprocess.run([
                    "javac", "--release", "9", "-proc:none", "-g:none",
                    "-encoding", "UTF-8",
                    "-classpath", str(root / "empty-classpath"),
                    "-sourcepath", str(root / "empty-sourcepath"),
                    "-d", str(target),
                    str(src / relative),
                ], text=True, capture_output=True, timeout=35)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                blob = (target / entry).read_bytes()
                output.writestr(entry, blob)
                expected[entry] = digest(blob)
        return src, artifact, expected, digest(artifact.read_bytes())

    def test_real_java9_collision_build_and_inverse_original_identity_parity(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            sources, original, classes, original_hash = self.make_original(root)
            report = verify_standalone_sources(
                original, sources, root / "verified",
                original_sha256=original_hash,
                class_sha256=classes,
                compile_aliases={ORIGINAL: ALIAS},
            )
            self.assertTrue(report["all_passed"])
            self.assertEqual(report["total_classes"], 2)
            self.assertEqual(report["compile_only_class_alias_count"], 1)
            self.assertTrue(report["canonical_source_modified"] is False)
            self.assertTrue(
                (root / "verified" / "classes" / ALIAS).is_file()
            )
            self.assertTrue(
                (root / "verified" / "restored-classfiles" / ORIGINAL).is_file()
            )
            self.assertTrue(
                (root / "verified" / "restored-classfiles" / CHILD).is_file()
            )
            self.assertEqual(
                (sources / "rs/t.java").read_text(encoding="utf-8"),
                NODE_SOURCE,
            )
            self.assertTrue(all(
                row["ordered_symbolic_instruction_parity"]
                for row in report["results"]
            ))
            self.assertFalse(report["complete_v311_source_recovery"])

    def test_no_alias_must_refuse_legacy_shadowing(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            sources, original, classes, original_hash = self.make_original(root)
            output = root / "refused"
            with self.assertRaisesRegex(
                ValueError, "CLASS_PACKAGE_COLLISION_REMAINS"
            ):
                verify_standalone_sources(
                    original, sources, output,
                    original_sha256=original_hash,
                    class_sha256=classes,
                )
            self.assertFalse(output.exists())

    def test_alias_cannot_change_package_or_shadow_original_member(self):
        for mapping, reason in [
            ({ORIGINAL: "another/Changed.class"}, "MUST_PRESERVE_PACKAGE"),
            ({ORIGINAL: CHILD}, "TARGET_EXISTS_IN_ORIGINAL"),
            ({CHILD: "rs/t/f.class"}, "OLD_CLASS_NOT_SELECTED"),
        ]:
            with self.subTest(mapping=mapping):
                with self.assertRaisesRegex(StandaloneAliasError, reason):
                    validate_compile_aliases(
                        {ORIGINAL, CHILD}, mapping, {ORIGINAL, CHILD},
                    )

    def test_source_rewrite_only_types_declaration_and_constructor(self):
        rewritten = rename_owned_class_source(
            NODE_SOURCE, old_entry=ORIGINAL, alias_entry=ALIAS
        )
        self.assertIn("class RecoveredNodeV311", rewritten)
        self.assertIn("public RecoveredNodeV311 d;", rewritten)
        self.assertIn("public RecoveredNodeV311()", rewritten)
        self.assertIn("package rs;", rewritten)
        self.assertEqual(
            NODE_SOURCE, NODE_SOURCE
        )  # canonical source immutable

    def test_ambiguous_class_identifier_refuses_before_touching_outputs(self):
        unsafe = NODE_SOURCE.replace(
            "public t() {}", "public t() { t = null; }"
        )
        with self.assertRaisesRegex(StandaloneAliasError, "AMBIGUOUS_JAVA_IDENTIFIER"):
            rename_owned_class_source(
                unsafe, old_entry=ORIGINAL, alias_entry=ALIAS
            )

    def test_external_source_reference_needs_explicit_review(self):
        ensure_no_external_alias_refs(CHILD_SOURCE, old_entry=ORIGINAL)
        with self.assertRaisesRegex(StandaloneAliasError, "EXTERNAL_SOURCE_REFERENCE"):
            ensure_no_external_alias_refs(
                CHILD_SOURCE.replace(
                    "public class f {", "public class f { public t linked;"
                ),
                old_entry=ORIGINAL,
            )

    def test_unverified_alias_target_name_is_rejected(self):
        for target in ("rs/../../Unsafe.class", "rs/recovered-name.class"):
            with self.subTest(target=target):
                with self.assertRaisesRegex(StandaloneAliasError, "CLASS_PATH_INVALID"):
                    validate_compile_aliases(
                        {ORIGINAL, CHILD}, {ORIGINAL: target}, {ORIGINAL, CHILD}
                    )

    def test_compile_remap_refuses_reflection_string_alias_mention(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            sources, original, classes, original_hash = self.make_original(root)
            # Deliberately introduce the future alias name into a string
            # literal. Constant-pool inverse remapper must not rewrite it.
            path = sources / "rs/t.java"
            path.write_text(path.read_text(encoding="utf-8").replace(
                "public t() {}",
                'public t() {} public String note() { return "rs/RecoveredNodeV311"; }'
            ), encoding="utf-8")
            dest = root / "not-admitted"
            with self.assertRaisesRegex(ValueError, "COMPILE_ALIAS_INVERSE_CLASSFILE_REFUSED"):
                verify_standalone_sources(
                    original, sources, dest,
                    original_sha256=original_hash, class_sha256=classes,
                    compile_aliases={ORIGINAL: ALIAS},
                )
            self.assertFalse((dest / "SOURCE-REBUILD-VERIFY.json").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)

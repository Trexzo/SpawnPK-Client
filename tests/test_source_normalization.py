from __future__ import annotations

import struct
from pathlib import Path
import subprocess
import tempfile
import unittest
import zipfile

from spk_recovery.source_normalization import (
    SourceNormalizationError,
    normalize_procyon_source,
)


def _u1(value: int) -> bytes:
    return struct.pack(">B", value)


def _u2(value: int) -> bytes:
    return struct.pack(">H", value)


def _u4(value: int) -> bytes:
    return struct.pack(">I", value)


def _utf8(value: str) -> bytes:
    raw = value.encode("utf-8")
    return _u1(1) + _u2(len(raw)) + raw


def _class(index: int) -> bytes:
    return _u1(7) + _u2(index)


def _synthetic_switch_class(
    internal_name: str = "pkg/SwitchMap",
    *,
    class_access: int = 0x1020,
    field_name: str | None = "a",
) -> bytes:
    cp = [
        _utf8(internal_name),      # 1
        _class(1),                 # 2
        _utf8("java/lang/Object"), # 3
        _class(3),                 # 4
    ]
    field_name_index = 0
    field_desc_index = 0
    if field_name is not None:
        field_name_index = len(cp) + 1
        cp.append(_utf8(field_name))
        field_desc_index = len(cp) + 1
        cp.append(_utf8("[I"))
    clinit_index = len(cp) + 1
    cp.append(_utf8("<clinit>"))
    void_desc_index = len(cp) + 1
    cp.append(_utf8("()V"))
    code_index = len(cp) + 1
    cp.append(_utf8("Code"))

    out = bytearray()
    out += _u4(0xCAFEBABE)
    out += _u2(0)
    out += _u2(52)
    out += _u2(len(cp) + 1)
    for entry in cp:
        out += entry

    out += _u2(class_access)
    out += _u2(2)
    out += _u2(4)
    out += _u2(0)

    if field_name is None:
        out += _u2(0)
    else:
        out += _u2(1)
        out += _u2(0x1018)
        out += _u2(field_name_index)
        out += _u2(field_desc_index)
        out += _u2(0)

    out += _u2(1)
    out += _u2(0x0008)
    out += _u2(clinit_index)
    out += _u2(void_desc_index)
    out += _u2(1)
    code = _u2(0) + _u2(0) + _u4(1) + bytes([0xB1]) + _u2(0) + _u2(0)
    out += _u2(code_index)
    out += _u4(len(code))
    out += code
    out += _u2(0)
    return bytes(out)


def _shadow_owner_fixture(root: Path) -> Path:
    legal = root / "legal"
    current = legal / "pkg" / "A.java"
    shadow = legal / "pkg" / "shadow" / "A.java"
    current.parent.mkdir(parents=True)
    shadow.parent.mkdir(parents=True)
    current.write_text(
        "package pkg;\n"
        "public class A {\n"
        "    public static A[] A;\n"
        "    public static A[] B;\n"
        "    public static void m(final pkg.shadow.A A) {\n"
        "        pkg.A.A = new A[1];\n"
        "        pkg.A.B = pkg.A.A;\n"
        "        A.ping();\n"
        "    }\n"
        "}\n",
        encoding="utf-8",
    )
    shadow.write_text(
        "package pkg.shadow;\n"
        "public class A {\n"
        "    private static Object A;\n"
        "    private static Object B;\n"
        "    public void ping() {}\n"
        "}\n",
        encoding="utf-8",
    )
    classes = root / "classes"
    classes.mkdir()
    proc = subprocess.run(
        ["javac", "-d", str(classes), str(current), str(shadow)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if proc.returncode != 0:
        raise AssertionError("javac fixture failed: " + proc.stderr)
    jar = root / "readable.jar"
    with zipfile.ZipFile(jar, "w") as z:
        for class_file in sorted(classes.rglob("*.class")):
            z.write(
                class_file,
                class_file.relative_to(classes).as_posix(),
            )
    return jar


def _hierarchy_shadow_fixture(
    root: Path,
    *,
    inherited: bool = False,
    object_shadow: bool = False,
    private_shadow: bool = False,
    inherited_target: bool = False,
) -> Path:
    legal = root / "hierarchy-legal"
    pkg = legal / "pkg"
    pkg.mkdir(parents=True)
    sources: list[Path] = []

    if inherited:
        base = pkg / "Base.java"
        shadow_type = "Object" if object_shadow else "int"
        visibility = "private" if private_shadow else "public"
        inherited_target_line = (
            "    public static int x;\n" if inherited_target else ""
        )
        base.write_text(
            "package pkg;\n"
            "public class Base {\n"
            f"    {visibility} static {shadow_type} h;\n"
            + inherited_target_line
            + "}\n",
            encoding="utf-8",
        )
        sources.append(base)
        current = pkg / "h.java"
        target_decl = "" if inherited_target else "    public static int x;\n"
        current.write_text(
            "package pkg;\n"
            "public class h extends Base {\n"
            + target_decl
            + "    public static void m() {\n"
            "        pkg.h.x = 7;\n"
            "        int y = pkg.h.x;\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )
    else:
        current = pkg / "h.java"
        shadow_type = "Object" if object_shadow else "int"
        current.write_text(
            "package pkg;\n"
            "public class h {\n"
            f"    public static {shadow_type} h;\n"
            "    public static int x;\n"
            "    public static void m() {\n"
            "        pkg.h.x = 7;\n"
            "        int y = pkg.h.x;\n"
            "    }\n"
            "}\n",
            encoding="utf-8",
        )
    sources.append(current)

    classes = root / "hierarchy-classes"
    classes.mkdir()
    proc = subprocess.run(
        ["javac", "-d", str(classes), *map(str, sources)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if proc.returncode != 0:
        raise AssertionError("javac hierarchy fixture failed: " + proc.stderr)

    jar = root / "hierarchy-readable.jar"
    with zipfile.ZipFile(jar, "w") as z:
        for class_file in sorted(classes.rglob("*.class")):
            z.write(
                class_file,
                class_file.relative_to(classes).as_posix(),
            )
    return jar


def _compile_java_fixture(root: Path, files: dict[str, str]) -> Path:
    legal = root / "custom-legal"
    sources: list[Path] = []
    for rel, content in sorted(files.items()):
        path = legal / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        sources.append(path)
    classes = root / "custom-classes"
    classes.mkdir()
    proc = subprocess.run(
        ["javac", "-d", str(classes), *map(str, sources)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if proc.returncode != 0:
        raise AssertionError("javac custom fixture failed: " + proc.stderr)
    jar = root / "custom-readable.jar"
    with zipfile.ZipFile(jar, "w") as z:
        for class_file in sorted(classes.rglob("*.class")):
            z.write(class_file, class_file.relative_to(classes).as_posix())
    return jar


class ProcyonSourceNormalizationTests(unittest.TestCase):
    def test_reconstructs_proven_synthetic_switch_class(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "src" / "pkg" / "SwitchMap.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package pkg;\n\n"
                "synthetic class SwitchMap\n"
                "{\n"
                "    static {\n"
                "        a = new int[2];\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )
            jar = root / "readable.jar"
            with zipfile.ZipFile(jar, "w") as z:
                z.writestr(
                    "pkg/SwitchMap.class",
                    _synthetic_switch_class(),
                )

            report = normalize_procyon_source(root / "src", jar)
            text = source.read_text(encoding="utf-8")

            self.assertIn("class SwitchMap", text)
            self.assertNotIn("synthetic class", text)
            self.assertIn("static final int[] a;", text)
            self.assertEqual(report["summary"]["synthetic_class_count"], 1)
            self.assertEqual(report["summary"]["synthetic_field_count"], 1)
            self.assertEqual(report["summary"]["action_count"], 1)

    def test_synthetic_pseudo_syntax_fails_without_exact_bytecode_proof(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "src" / "pkg" / "SwitchMap.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package pkg;\n\nsynthetic class SwitchMap\n{\n}\n",
                encoding="utf-8",
            )
            jar = root / "readable.jar"
            with zipfile.ZipFile(jar, "w") as z:
                z.writestr(
                    "pkg/SwitchMap.class",
                    _synthetic_switch_class(
                        class_access=0x0020,
                        field_name=None,
                    ),
                )

            with self.assertRaises(SourceNormalizationError):
                normalize_procyon_source(root / "src", jar)

    def test_qualifies_exact_shadowed_self_static_field_owners(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _shadow_owner_fixture(root)
            source = root / "src" / "pkg" / "A.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package pkg;\n"
                "public class A {\n"
                "    public static A[] A;\n"
                "    public static A[] B;\n"
                "    public static void m(final pkg.shadow.A A) {\n"
                "        A.A = new A[1];\n"
                "        A.B = A.A;\n"
                "        A.ping();\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )

            report = normalize_procyon_source(root / "src", jar)
            text = source.read_text(encoding="utf-8")

            self.assertIn("pkg.A.A = new A[1];", text)
            self.assertIn("pkg.A.B = pkg.A.A;", text)
            self.assertIn("A.ping();", text)
            self.assertEqual(
                report["summary"][
                    "shadowed_self_static_field_method_count"
                ],
                1,
            )
            self.assertEqual(
                report["summary"][
                    "shadowed_self_static_field_reference_count"
                ],
                3,
            )
            action = next(
                row for row in report["actions"]
                if row["kind"]
                == "shadowed_self_static_field_owner_qualification"
            )
            self.assertEqual(
                action["field_access_counts"],
                {"A": 2, "B": 1},
            )
            self.assertEqual(
                action["shadow_parameter_type"],
                "pkg/shadow/A",
            )

    def test_shadowed_self_static_field_ignores_literals_and_comments(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _shadow_owner_fixture(root)
            source = root / "src" / "pkg" / "A.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package pkg;\n"
                "public class A {\n"
                "    public static A[] A;\n"
                "    public static A[] B;\n"
                "    public static void m(final pkg.shadow.A A) {\n"
                "        A.A = new A[1];\n"
                "        A.B = A.A;\n"
                "        String literal = \"A.A A.B\"; // A.A\n"
                "        /* A.B */ A.ping();\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )

            report = normalize_procyon_source(root / "src", jar)
            text = source.read_text(encoding="utf-8")

            self.assertIn("pkg.A.A = new A[1];", text)
            self.assertIn("pkg.A.B = pkg.A.A;", text)
            self.assertIn('String literal = "A.A A.B"; // A.A', text)
            self.assertIn("/* A.B */ A.ping();", text)
            self.assertEqual(
                report["summary"][
                    "shadowed_self_static_field_reference_count"
                ],
                3,
            )

    def test_shadowed_self_static_field_count_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _shadow_owner_fixture(root)
            source = root / "src" / "pkg" / "A.java"
            source.parent.mkdir(parents=True)
            original = (
                "package pkg;\n"
                "public class A {\n"
                "    public static A[] A;\n"
                "    public static A[] B;\n"
                "    public static void m(final pkg.shadow.A A) {\n"
                "        A.A = new A[1];\n"
                "        A.ping();\n"
                "    }\n"
                "}\n"
            )
            source.write_text(original, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)

            self.assertEqual(
                source.read_text(encoding="utf-8"),
                original,
            )
            self.assertEqual(
                report["summary"][
                    "shadowed_self_static_field_method_count"
                ],
                0,
            )
            self.assertEqual(
                report["summary"][
                    "shadowed_self_static_field_reference_count"
                ],
                0,
            )

    def test_qualifies_direct_primitive_hierarchy_shadow(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _hierarchy_shadow_fixture(root)
            source = root / "src" / "pkg" / "h.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package pkg;\n"
                "public class h {\n"
                "    public static int h;\n"
                "    public static int x;\n"
                "    public static void m() {\n"
                "        h.x = 7;\n"
                "        int y = h.x;\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )

            report = normalize_procyon_source(root / "src", jar)
            text = source.read_text(encoding="utf-8")

            self.assertIn("pkg.h.x = 7;", text)
            self.assertIn("int y = pkg.h.x;", text)
            self.assertEqual(
                report["summary"][
                    "hierarchy_shadowed_self_static_field_reference_count"
                ],
                2,
            )

    def test_qualifies_inherited_primitive_hierarchy_shadow(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _hierarchy_shadow_fixture(root, inherited=True)
            source = root / "src" / "pkg" / "h.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package pkg;\n"
                "public class h extends Base {\n"
                "    public static int x;\n"
                "    public static void m() {\n"
                "        h.x = 7;\n"
                "        int y = h.x;\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )

            report = normalize_procyon_source(root / "src", jar)
            text = source.read_text(encoding="utf-8")

            self.assertIn("pkg.h.x = 7;", text)
            self.assertIn("int y = pkg.h.x;", text)
            action = next(
                row
                for row in report["actions"]
                if row["kind"]
                == "hierarchy_shadowed_self_static_field_owner_qualification"
            )
            self.assertEqual(action["primitive_shadow_owners"], ["pkg/Base"])

    def test_qualifies_inherited_static_target_with_symbolic_subclass_owner(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _hierarchy_shadow_fixture(
                root,
                inherited=True,
                inherited_target=True,
            )
            source = root / "src" / "pkg" / "h.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package pkg;\n"
                "public class h extends Base {\n"
                "    public static void m() {\n"
                "        h.x = 7;\n"
                "        int y = h.x;\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )

            report = normalize_procyon_source(root / "src", jar)
            text = source.read_text(encoding="utf-8")

            self.assertIn("pkg.h.x = 7;", text)
            self.assertIn("int y = pkg.h.x;", text)
            self.assertEqual(
                report["summary"][
                    "hierarchy_shadowed_self_static_field_reference_count"
                ],
                2,
            )

    def test_object_typed_same_name_field_does_not_qualify(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _hierarchy_shadow_fixture(
                root,
                inherited=True,
                object_shadow=True,
            )
            source = root / "src" / "pkg" / "h.java"
            source.parent.mkdir(parents=True)
            original = (
                "package pkg;\n"
                "public class h extends Base {\n"
                "    public static int x;\n"
                "    public static void m() {\n"
                "        h.x = 7;\n"
                "        int y = h.x;\n"
                "    }\n"
                "}\n"
            )
            source.write_text(original, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)

            self.assertEqual(source.read_text(encoding="utf-8"), original)
            self.assertEqual(
                report["summary"][
                    "hierarchy_shadowed_self_static_field_reference_count"
                ],
                0,
            )

    def test_private_inherited_primitive_shadow_is_not_visible(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _hierarchy_shadow_fixture(
                root,
                inherited=True,
                private_shadow=True,
            )
            source = root / "src" / "pkg" / "h.java"
            source.parent.mkdir(parents=True)
            original = (
                "package pkg;\n"
                "public class h extends Base {\n"
                "    public static int x;\n"
                "    public static void m() {\n"
                "        h.x = 7;\n"
                "        int y = h.x;\n"
                "    }\n"
                "}\n"
            )
            source.write_text(original, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)

            self.assertEqual(source.read_text(encoding="utf-8"), original)
            self.assertEqual(
                report["summary"][
                    "hierarchy_shadowed_self_static_field_reference_count"
                ],
                0,
            )

    def test_same_name_local_value_binding_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _hierarchy_shadow_fixture(root)
            source = root / "src" / "pkg" / "h.java"
            source.parent.mkdir(parents=True)
            original = (
                "package pkg;\n"
                "public class h {\n"
                "    public static int h;\n"
                "    public static int x;\n"
                "    public static void m() {\n"
                "        Object h = null;\n"
                "        h.x = 7;\n"
                "        int y = h.x;\n"
                "    }\n"
                "}\n"
            )
            source.write_text(original, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)

            self.assertEqual(source.read_text(encoding="utf-8"), original)
            self.assertEqual(
                report["summary"][
                    "hierarchy_shadowed_self_static_field_reference_count"
                ],
                0,
            )

    def test_hierarchy_shadow_count_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _hierarchy_shadow_fixture(root)
            source = root / "src" / "pkg" / "h.java"
            source.parent.mkdir(parents=True)
            original = (
                "package pkg;\n"
                "public class h {\n"
                "    public static int h;\n"
                "    public static int x;\n"
                "    public static void m() {\n"
                "        h.x = 7;\n"
                "        int y = h.x;\n"
                "        int z = h.x;\n"
                "    }\n"
                "}\n"
            )
            source.write_text(original, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)

            self.assertEqual(source.read_text(encoding="utf-8"), original)
            self.assertEqual(
                report["summary"][
                    "hierarchy_shadowed_self_static_field_reference_count"
                ],
                0,
            )

    def test_hierarchy_shadow_ignores_literals_and_comments(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _hierarchy_shadow_fixture(root)
            source = root / "src" / "pkg" / "h.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package pkg;\n"
                "public class h {\n"
                "    public static int h;\n"
                "    public static int x;\n"
                "    public static void m() {\n"
                "        h.x = 7;\n"
                "        int y = h.x;\n"
                '        String s = "h.x"; // h.x\n'
                "        /* h.x */\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )

            report = normalize_procyon_source(root / "src", jar)
            text = source.read_text(encoding="utf-8")

            self.assertIn('String s = "h.x"; // h.x', text)
            self.assertIn("/* h.x */", text)
            self.assertEqual(
                report["summary"][
                    "hierarchy_shadowed_self_static_field_reference_count"
                ],
                2,
            )

    def test_primitive_same_name_parameter_does_not_block_exact_owner(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "pkg/h.java": (
                        "package pkg;\n"
                        "public class h {\n"
                        "    public int h;\n"
                        "    public static int x;\n"
                        "    public static void m(int h) {\n"
                        "        pkg.h.x = 1;\n"
                        "        int y = pkg.h.x;\n"
                        "    }\n"
                        "}\n"
                    )
                },
            )
            source = root / "src" / "pkg" / "h.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package pkg;\n"
                "public class h {\n"
                "    public int h;\n"
                "    public static int x;\n"
                "    public static void m(int h) {\n"
                "        h.x = 1;\n"
                "        int y = h.x;\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )

            report = normalize_procyon_source(root / "src", jar)
            text = source.read_text(encoding="utf-8")

            self.assertIn("pkg.h.x = 1;", text)
            self.assertIn("int y = pkg.h.x;", text)
            self.assertEqual(
                report["summary"][
                    "hierarchy_shadowed_self_static_field_reference_count"
                ],
                2,
            )

    def test_reference_same_name_parameter_still_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "pkg/h.java": (
                        "package pkg;\n"
                        "public class h {\n"
                        "    public int h;\n"
                        "    public static int x;\n"
                        "    public static void m(Object h) {\n"
                        "        pkg.h.x = 1;\n"
                        "        int y = pkg.h.x;\n"
                        "    }\n"
                        "}\n"
                    )
                },
            )
            source = root / "src" / "pkg" / "h.java"
            source.parent.mkdir(parents=True)
            original = (
                "package pkg;\n"
                "public class h {\n"
                "    public int h;\n"
                "    public static int x;\n"
                "    public static void m(Object h) {\n"
                "        h.x = 1;\n"
                "        int y = h.x;\n"
                "    }\n"
                "}\n"
            )
            source.write_text(original, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)

            self.assertEqual(source.read_text(encoding="utf-8"), original)
            self.assertEqual(
                report["summary"][
                    "hierarchy_shadowed_self_static_field_reference_count"
                ],
                0,
            )

    def test_object_local_blocks_only_its_lexical_scope(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "pkg/h.java": (
                        "package pkg;\n"
                        "public class h {\n"
                        "    public int h;\n"
                        "    public static int x;\n"
                        "    public static void m() {\n"
                        "        pkg.h.x = 1;\n"
                        "        { Object h = null; }\n"
                        "        int y = pkg.h.x;\n"
                        "    }\n"
                        "}\n"
                    )
                },
            )
            source = root / "src" / "pkg" / "h.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package pkg;\n"
                "public class h {\n"
                "    public int h;\n"
                "    public static int x;\n"
                "    public static void m() {\n"
                "        h.x = 1;\n"
                "        { Object h = null; h.x = 99; }\n"
                "        int y = h.x;\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )

            report = normalize_procyon_source(root / "src", jar)
            text = source.read_text(encoding="utf-8")

            self.assertIn("pkg.h.x = 1;", text)
            self.assertIn("{ Object h = null; h.x = 99; }", text)
            self.assertIn("int y = pkg.h.x;", text)
            self.assertEqual(
                report["summary"][
                    "hierarchy_shadowed_self_static_field_reference_count"
                ],
                2,
            )

    def test_source_subset_uses_sufficient_exact_field_access_counts(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "pkg/h.java": (
                        "package pkg;\n"
                        "public class h {\n"
                        "    public int h;\n"
                        "    public static int x;\n"
                        "    public static void m() {\n"
                        "        pkg.h.x = 1;\n"
                        "        int y = pkg.h.x;\n"
                        "    }\n"
                        "}\n"
                    )
                },
            )
            source = root / "src" / "pkg" / "h.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package pkg;\n"
                "public class h {\n"
                "    public int h;\n"
                "    public static int x;\n"
                "    public static void m() {\n"
                "        h.x = 1;\n"
                "        int y = pkg.h.x;\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )

            report = normalize_procyon_source(root / "src", jar)
            text = source.read_text(encoding="utf-8")

            self.assertIn("pkg.h.x = 1;", text)
            self.assertEqual(
                report["summary"][
                    "hierarchy_shadowed_self_static_field_reference_count"
                ],
                1,
            )

    def test_overloads_are_bound_by_source_parameter_descriptor_shape(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "pkg/h.java": (
                        "package pkg;\n"
                        "public class h {\n"
                        "    public int h;\n"
                        "    public static int x;\n"
                        "    public static void m(String s) { pkg.h.x = 1; }\n"
                        "    public static void m(Boolean b) { pkg.h.x = 2; }\n"
                        "}\n"
                    )
                },
            )
            source = root / "src" / "pkg" / "h.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package pkg;\n"
                "public class h {\n"
                "    public int h;\n"
                "    public static int x;\n"
                "    public static void m(String s) { h.x = 1; }\n"
                "    public static void m(Boolean b) { h.x = 2; }\n"
                "}\n",
                encoding="utf-8",
            )

            report = normalize_procyon_source(root / "src", jar)
            text = source.read_text(encoding="utf-8")

            self.assertEqual(text.count("pkg.h.x"), 2)
            actions = [
                row for row in report["actions"]
                if row["kind"]
                == "hierarchy_shadowed_self_static_field_owner_qualification"
            ]
            self.assertEqual(len(actions), 2)
            self.assertEqual(
                {row["method_descriptor"] for row in actions},
                {"(Ljava/lang/String;)V", "(Ljava/lang/Boolean;)V"},
            )

    def test_relative_nested_parameter_type_matches_exact_descriptor(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "pkg/h.java": (
                        "package pkg;\n"
                        "public class h { public static class a {} }\n"
                    ),
                    "pkg/t.java": (
                        "package pkg;\n"
                        "public class t {\n"
                        "    public int t;\n"
                        "    public static int[] b;\n"
                        "    public static void m(h.a a) {\n"
                        "        pkg.t.b = new int[1];\n"
                        "        int y = pkg.t.b.length;\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )
            source = root / "src" / "pkg" / "t.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package pkg;\n"
                "public class t {\n"
                "    public int t;\n"
                "    public static int[] b;\n"
                "    public static void m(h.a a) {\n"
                "        t.b = new int[1];\n"
                "        int y = t.b.length;\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )

            report = normalize_procyon_source(root / "src", jar)
            text = source.read_text(encoding="utf-8")

            self.assertIn("pkg.t.b = new int[1];", text)
            self.assertIn("int y = pkg.t.b.length;", text)
            action = next(
                row for row in report["actions"]
                if row["kind"]
                == "hierarchy_shadowed_self_static_field_owner_qualification"
            )
            self.assertEqual(action["method_descriptor"], "(Lpkg/h$a;)V")

    def test_static_initializer_uses_exact_clinit_field_proof(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "pkg/h.java": (
                        "package pkg;\n"
                        "public class h {\n"
                        "    public int h;\n"
                        "    public static int x;\n"
                        "    static { pkg.h.x = 1; }\n"
                        "}\n"
                    )
                },
            )
            source = root / "src" / "pkg" / "h.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package pkg;\n"
                "public class h {\n"
                "    public int h;\n"
                "    public static int x;\n"
                "    static { h.x = 1; }\n"
                "}\n",
                encoding="utf-8",
            )

            report = normalize_procyon_source(root / "src", jar)
            text = source.read_text(encoding="utf-8")

            self.assertIn("static { pkg.h.x = 1; }", text)
            action = next(
                row for row in report["actions"]
                if row.get("method_name") == "<clinit>"
            )
            self.assertEqual(action["method_descriptor"], "()V")

    def test_discarded_string_expression_preserves_evaluation(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "src" / "pkg" / "A.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package pkg;\n"
                "class A\n"
                "{\n"
                "    void m(int n)\n"
                "    {\n"
                "        \"value=\" + call(n);\n"
                "    }\n"
                "    String call(int n) { return String.valueOf(n); }\n"
                "}\n",
                encoding="utf-8",
            )
            jar = root / "readable.jar"
            with zipfile.ZipFile(jar, "w"):
                pass

            report = normalize_procyon_source(root / "src", jar)
            text = source.read_text(encoding="utf-8")

            self.assertIn("final String recoveredDiscardedExpression_", text)
            self.assertIn('= "value=" + call(n);', text)
            self.assertEqual(
                report["summary"]["discarded_string_expression_count"],
                1,
            )

    def test_discarded_string_expression_fails_outside_executable_depth(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "src" / "pkg" / "A.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package pkg;\n"
                "class A\n"
                "{\n"
                "    \"value=\" + 1;\n"
                "}\n",
                encoding="utf-8",
            )
            jar = root / "readable.jar"
            with zipfile.ZipFile(jar, "w"):
                pass

            with self.assertRaises(SourceNormalizationError):
                normalize_procyon_source(root / "src", jar)


if __name__ == "__main__":
    unittest.main()

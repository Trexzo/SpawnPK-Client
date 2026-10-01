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


def _import_shadow_parameter_fixture(
    root: Path,
    *,
    descriptor_owner: str = "imported",
) -> Path:
    legal = root / ("import-shadow-" + descriptor_owner)
    other = legal / "other" / "h.java"
    local = legal / "p" / "h.java"
    current = legal / "p" / "Current.java"
    other.parent.mkdir(parents=True, exist_ok=True)
    local.parent.mkdir(parents=True, exist_ok=True)

    other.write_text(
        "package other;\n"
        "public class h {\n"
        "    public void a(final int n, final int[] array) {}\n"
        "}\n",
        encoding="utf-8",
    )
    local.write_text(
        "package p;\n"
        "public class h {\n"
        "    public void a(final Object value) {}\n"
        "    public int a(final int x, final int y, final int z) {\n"
        "        return x + y + z;\n"
        "    }\n"
        "}\n",
        encoding="utf-8",
    )
    parameter_type = "other.h" if descriptor_owner == "imported" else "p.h"
    body = (
        "        if (h != null) { h.a(n, new int[] { 1 }); }\n"
        if descriptor_owner == "imported"
        else "        if (h != null) { h.a(Integer.valueOf(n)); }\n"
    )
    current.write_text(
        "package p;\n"
        "import other.h;\n"
        "public class Current {\n"
        "    public static void m(final "
        + parameter_type
        + " h, final int n) {\n"
        + body
        + "    }\n"
        "}\n",
        encoding="utf-8",
    )

    classes = root / ("import-shadow-classes-" + descriptor_owner)
    classes.mkdir()

    first_sources = [other, local]
    proc = subprocess.run(
        ["javac", "-d", str(classes), *map(str, first_sources)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if proc.returncode != 0:
        raise AssertionError(
            "javac import-shadow dependency fixture failed: " + proc.stderr
        )

    proc = subprocess.run(
        [
            "javac",
            "-cp",
            str(classes),
            "-d",
            str(classes),
            str(current),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if proc.returncode != 0:
        raise AssertionError(
            "javac import-shadow current fixture failed: " + proc.stderr
        )

    jar = root / ("import-shadow-" + descriptor_owner + ".jar")
    with zipfile.ZipFile(jar, "w") as z:
        for class_file in sorted(classes.rglob("*.class")):
            z.write(
                class_file,
                class_file.relative_to(classes).as_posix(),
            )
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

    def test_qualifies_primitive_array_hierarchy_shadow(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "pkg/h.java": (
                        "package pkg;\n"
                        "public class h {\n"
                        "    public int[] h;\n"
                        "    public static int x;\n"
                        "    public static void m() {\n"
                        "        pkg.h.x = 7;\n"
                        "        int y = pkg.h.x;\n"
                        "    }\n"
                        "    static { pkg.h.x = 9; }\n"
                        "}\n"
                    )
                },
            )
            source = root / "src" / "pkg" / "h.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package pkg;\n"
                "public class h {\n"
                "    public int[] h;\n"
                "    public static int x;\n"
                "    public static void m() {\n"
                "        h.x = 7;\n"
                "        int y = h.x;\n"
                "    }\n"
                "    static { h.x = 9; }\n"
                "}\n",
                encoding="utf-8",
            )

            report = normalize_procyon_source(root / "src", jar)
            text = source.read_text(encoding="utf-8")

            self.assertIn("pkg.h.x = 7;", text)
            self.assertIn("int y = pkg.h.x;", text)
            self.assertIn("static { pkg.h.x = 9; }", text)
            self.assertEqual(
                report["summary"][
                    "hierarchy_shadowed_self_static_field_reference_count"
                ],
                3,
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

    def test_primitive_parameter_shadowed_self_static_owner_is_qualified(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "pkg/i.java": (
                        "package pkg;\n"
                        "public class i {\n"
                        "    public static int[] c = new int[2];\n"
                        "    public static void m(int i) {\n"
                        "        pkg.i.c[0] = i;\n"
                        "        pkg.i.c[1] = i + 1;\n"
                        "    }\n"
                        "}\n"
                    )
                },
            )
            source = root / "src" / "pkg" / "i.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package pkg;\n"
                "public class i {\n"
                "    public static int[] c = new int[2];\n"
                "    public static void m(int i) {\n"
                "        i.c[0] = i;\n"
                "        i.c[1] = i + 1;\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )

            before = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "before-primitive-parameter-classes"),
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(before.returncode, 0)
            self.assertIn("int cannot be dereferenced", before.stderr)

            report = normalize_procyon_source(root / "src", jar)
            normalized = source.read_text(encoding="utf-8")

            self.assertIn("pkg.i.c[0] = i;", normalized)
            self.assertIn("pkg.i.c[1] = i + 1;", normalized)
            action = next(
                row
                for row in report["actions"]
                if row["kind"]
                == "primitive_scope_shadowed_self_static_field_owner_qualification"
            )
            self.assertTrue(action["primitive_parameter_shadow"])
            self.assertEqual(
                action["primitive_local_shadow_scope_count"],
                0,
            )
            self.assertEqual(action["method_descriptor"], "(I)V")
            self.assertEqual(
                action["field_access_counts"],
                {"pkg/i.c": 2},
            )
            self.assertEqual(
                action["total_field_access_counts"],
                {"pkg/i.c": 2},
            )
            self.assertEqual(action["replacement_count"], 2)
            self.assertEqual(
                report["summary"][
                    "primitive_scope_shadowed_self_static_field_reference_count"
                ],
                2,
            )

            after = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "after-primitive-parameter-classes"),
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(
                after.returncode,
                0,
                after.stdout + after.stderr,
            )

    def test_primitive_local_shadow_only_rewrites_its_lexical_scope(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "pkg/i.java": (
                        "package pkg;\n"
                        "public class i {\n"
                        "    public static int[] c = new int[2];\n"
                        "    public static void m() {\n"
                        "        { int i = 3; pkg.i.c[0] = i; }\n"
                        "        pkg.i.c[1] = 4;\n"
                        "    }\n"
                        "}\n"
                    )
                },
            )
            source = root / "src" / "pkg" / "i.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package pkg;\n"
                "public class i {\n"
                "    public static int[] c = new int[2];\n"
                "    public static void m() {\n"
                "        { int i = 3; i.c[0] = i; }\n"
                "        i.c[1] = 4;\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )

            report = normalize_procyon_source(root / "src", jar)
            normalized = source.read_text(encoding="utf-8")

            self.assertIn(
                "{ int i = 3; pkg.i.c[0] = i; }",
                normalized,
            )
            self.assertIn("i.c[1] = 4;", normalized)
            action = next(
                row
                for row in report["actions"]
                if row["kind"]
                == "primitive_scope_shadowed_self_static_field_owner_qualification"
            )
            self.assertFalse(action["primitive_parameter_shadow"])
            self.assertEqual(
                action["primitive_local_shadow_scope_count"],
                1,
            )
            self.assertEqual(action["replacement_count"], 1)
            self.assertEqual(
                action["total_field_access_counts"],
                {"pkg/i.c": 2},
            )

            after = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "after-primitive-local-classes"),
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(
                after.returncode,
                0,
                after.stdout + after.stderr,
            )

    def test_primitive_scope_shadow_count_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "pkg/i.java": (
                        "package pkg;\n"
                        "public class i {\n"
                        "    public static int[] c = new int[2];\n"
                        "    public static void m(int i) {\n"
                        "        pkg.i.c[0] = i;\n"
                        "    }\n"
                        "}\n"
                    )
                },
            )
            source = root / "src" / "pkg" / "i.java"
            source.parent.mkdir(parents=True)
            original = (
                "package pkg;\n"
                "public class i {\n"
                "    public static int[] c = new int[2];\n"
                "    public static void m(int i) {\n"
                "        i.c[0] = i;\n"
                "        i.c[1] = i + 1;\n"
                "    }\n"
                "}\n"
            )
            source.write_text(original, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)

            self.assertEqual(source.read_text(encoding="utf-8"), original)
            self.assertEqual(
                report["summary"][
                    "primitive_scope_shadowed_self_static_field_reference_count"
                ],
                0,
            )
            self.assertFalse(
                any(
                    row["kind"]
                    == "primitive_scope_shadowed_self_static_field_owner_qualification"
                    for row in report["actions"]
                )
            )

    def test_primitive_shadowed_instance_receiver_uses_this_field(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "dep/H.java": (
                        "package dep;\n"
                        "public class H {\n"
                        "    public float a(int x, int y) { return x + y; }\n"
                        "    public float b(int x, int y) { return x - y; }\n"
                        "}\n"
                    ),
                    "use/Current.java": (
                        "package use;\n"
                        "import dep.H;\n"
                        "public class Current {\n"
                        "    public H h = new H();\n"
                        "    public float m(int h) {\n"
                        "        return this.h.a(h, 0) + this.h.b(h, 1);\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )
            source = root / "src" / "use" / "Current.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package use;\n"
                "import dep.H;\n"
                "public class Current {\n"
                "    public H h = new H();\n"
                "    public float m(int h) {\n"
                "        return h.a(h, 0) + h.b(h, 1);\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )

            before = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "before-instance-receiver-classes"),
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(before.returncode, 0)
            self.assertIn("int cannot be dereferenced", before.stderr)

            report = normalize_procyon_source(root / "src", jar)
            normalized = source.read_text(encoding="utf-8")

            self.assertIn(
                "return this.h.a(h, 0) + this.h.b(h, 1);",
                normalized,
            )
            action = next(
                row
                for row in report["actions"]
                if row["kind"]
                == "primitive_shadowed_instance_field_receiver_qualification"
            )
            self.assertEqual(action["receiver_field_name"], "h")
            self.assertEqual(action["receiver_type_owner"], "dep/H")
            self.assertEqual(action["method_descriptor"], "(I)F")
            self.assertEqual(action["call_counts"], {"a": 1, "b": 1})
            self.assertEqual(action["replacement_count"], 2)
            self.assertEqual(
                report["summary"][
                    "primitive_shadowed_instance_receiver_reference_count"
                ],
                2,
            )

            after = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "after-instance-receiver-classes"),
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(
                after.returncode,
                0,
                after.stdout + after.stderr,
            )

    def test_primitive_shadowed_instance_receiver_count_mismatch_fails_closed(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "dep/H.java": (
                        "package dep;\n"
                        "public class H {\n"
                        "    public float a(int x, int y) { return x + y; }\n"
                        "}\n"
                    ),
                    "use/Current.java": (
                        "package use;\n"
                        "import dep.H;\n"
                        "public class Current {\n"
                        "    public H h = new H();\n"
                        "    public float m(int h) {\n"
                        "        return this.h.a(h, 0);\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )
            source = root / "src" / "use" / "Current.java"
            source.parent.mkdir(parents=True)
            original = (
                "package use;\n"
                "import dep.H;\n"
                "public class Current {\n"
                "    public H h = new H();\n"
                "    public float m(int h) {\n"
                "        return h.a(h, 0) + h.a(h, 1);\n"
                "    }\n"
                "}\n"
            )
            source.write_text(original, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)

            self.assertEqual(source.read_text(encoding="utf-8"), original)
            self.assertEqual(
                report["summary"][
                    "primitive_shadowed_instance_receiver_reference_count"
                ],
                0,
            )

    def test_reference_field_shadowed_self_static_owner_is_qualified(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "pkg/q.java": (
                        "package pkg;\n"
                        "public class q {\n"
                        "    public String q;\n"
                        "    public static int a = 1;\n"
                        "    public static int f = 2;\n"
                        "    public static int read() {\n"
                        "        return pkg.q.a + pkg.q.f;\n"
                        "    }\n"
                        "}\n"
                    )
                },
            )
            source = root / "src" / "pkg" / "q.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package pkg;\n"
                "public class q {\n"
                "    public String q;\n"
                "    public static int a = 1;\n"
                "    public static int f = 2;\n"
                "    public static int read() {\n"
                "        return q.a + q.f;\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )

            before = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "before-reference-self-classes"),
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(before.returncode, 0)
            self.assertIn(
                "non-static variable q cannot be referenced",
                before.stderr,
            )

            report = normalize_procyon_source(root / "src", jar)
            normalized = source.read_text(encoding="utf-8")

            self.assertIn("return pkg.q.a + pkg.q.f;", normalized)
            action = next(
                row
                for row in report["actions"]
                if row["kind"]
                == "reference_shadowed_self_static_field_owner_qualification"
            )
            self.assertEqual(action["method_descriptor"], "()I")
            self.assertEqual(action["reference_shadow_owners"], ["pkg/q"])
            self.assertEqual(
                action["field_access_counts"],
                {"pkg/q.a": 1, "pkg/q.f": 1},
            )
            self.assertEqual(action["replacement_count"], 2)
            self.assertEqual(
                report["summary"][
                    "reference_shadowed_self_static_field_reference_count"
                ],
                2,
            )

            after = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "after-reference-self-classes"),
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(
                after.returncode,
                0,
                after.stdout + after.stderr,
            )

    def test_reference_field_shadow_count_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "pkg/q.java": (
                        "package pkg;\n"
                        "public class q {\n"
                        "    public String q;\n"
                        "    public static int a = 1;\n"
                        "    public static int read() { return pkg.q.a; }\n"
                        "}\n"
                    )
                },
            )
            source = root / "src" / "pkg" / "q.java"
            source.parent.mkdir(parents=True)
            original = (
                "package pkg;\n"
                "public class q {\n"
                "    public String q;\n"
                "    public static int a = 1;\n"
                "    public static int read() { return q.a + q.a; }\n"
                "}\n"
            )
            source.write_text(original, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)

            self.assertEqual(source.read_text(encoding="utf-8"), original)
            self.assertEqual(
                report["summary"][
                    "reference_shadowed_self_static_field_reference_count"
                ],
                0,
            )

    def test_nested_type_static_field_shadow_forces_type_context(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "pkg/Base.java": (
                        "package pkg;\n"
                        "public class Base { public Object b; }\n"
                    ),
                    "pkg/Outer.java": (
                        "package pkg;\n"
                        "public class Outer extends Base {\n"
                        "    public static class b {\n"
                        "        public static int h = 7;\n"
                        "        public static int i = 8;\n"
                        "    }\n"
                        "}\n"
                    ),
                    "use/Current.java": (
                        "package use;\n"
                        "public class Current {\n"
                        "    public static int m() {\n"
                        "        return ((pkg.Outer.b)null).h"
                        " + ((pkg.Outer.b)null).i;\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )

            source = root / "src" / "use" / "Current.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package use;\n"
                "public class Current {\n"
                "    public static int m() {\n"
                "        return pkg.Outer.b.h + pkg.Outer.b.i;\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )

            before = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "before-classes"),
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(before.returncode, 0)
            self.assertIn(
                "non-static variable b cannot be referenced",
                before.stderr,
            )

            report = normalize_procyon_source(root / "src", jar)
            text = source.read_text(encoding="utf-8")

            self.assertIn("((pkg.Outer.b)null).h", text)
            self.assertIn("((pkg.Outer.b)null).i", text)
            self.assertEqual(
                report["summary"][
                    "shadowed_nested_static_field_method_count"
                ],
                1,
            )
            self.assertEqual(
                report["summary"][
                    "shadowed_nested_static_field_reference_count"
                ],
                2,
            )

            action = next(
                row
                for row in report["actions"]
                if row["kind"]
                == "shadowed_nested_static_field_owner_type_context"
            )
            self.assertEqual(action["method_descriptor"], "()I")
            self.assertEqual(
                action["nested_owners"],
                ["pkg/Outer$b"],
            )
            self.assertEqual(
                action["shadow_declaring_owners"],
                ["pkg/Base"],
            )
            self.assertEqual(
                action["field_access_counts"],
                {
                    "pkg/Outer$b.h": 1,
                    "pkg/Outer$b.i": 1,
                },
            )

            after = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "after-classes"),
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(
                after.returncode,
                0,
                after.stdout + after.stderr,
            )

    def test_nested_type_static_field_shadow_count_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "pkg/Base.java": (
                        "package pkg;\n"
                        "public class Base { public Object b; }\n"
                    ),
                    "pkg/Outer.java": (
                        "package pkg;\n"
                        "public class Outer extends Base {\n"
                        "    public static class b {\n"
                        "        public static int h = 7;\n"
                        "    }\n"
                        "}\n"
                    ),
                    "use/Current.java": (
                        "package use;\n"
                        "public class Current {\n"
                        "    public static int m() {\n"
                        "        return ((pkg.Outer.b)null).h;\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )

            source = root / "src" / "use" / "Current.java"
            source.parent.mkdir(parents=True)
            original = (
                "package use;\n"
                "public class Current {\n"
                "    public static int m() {\n"
                "        return pkg.Outer.b.h + pkg.Outer.b.h;\n"
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
                    "shadowed_nested_static_field_reference_count"
                ],
                0,
            )


    def test_nested_type_static_field_shadow_in_constructor_forces_type_context(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "pkg/Base.java": (
                        "package pkg;\n"
                        "public class Base { public Object b; }\n"
                    ),
                    "pkg/Outer.java": (
                        "package pkg;\n"
                        "public class Outer extends Base {\n"
                        "    public static class b {\n"
                        "        public static int h = 7;\n"
                        "        public static int i = 8;\n"
                        "    }\n"
                        "}\n"
                    ),
                    "use/Current.java": (
                        "package use;\n"
                        "public class Current {\n"
                        "    public int value;\n"
                        "    public Current() {\n"
                        "        value = ((pkg.Outer.b)null).h"
                        " + ((pkg.Outer.b)null).i;\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )

            source = root / "src" / "use" / "Current.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package use;\n"
                "public class Current {\n"
                "    public int value;\n"
                "    public Current() {\n"
                "        value = pkg.Outer.b.h + pkg.Outer.b.i;\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )

            before = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "before-constructor-classes"),
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(before.returncode, 0)

            report = normalize_procyon_source(root / "src", jar)
            normalized = source.read_text(encoding="utf-8")

            self.assertIn("((pkg.Outer.b)null).h", normalized)
            self.assertIn("((pkg.Outer.b)null).i", normalized)

            action = next(
                row
                for row in report["actions"]
                if (
                    row["kind"]
                    == "shadowed_nested_static_field_owner_type_context"
                    and row.get("method_name") == "<init>"
                )
            )
            self.assertEqual(action["method_descriptor"], "()V")
            self.assertEqual(action["replacement_count"], 2)

            after = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "after-constructor-classes"),
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(
                after.returncode,
                0,
                after.stdout + after.stderr,
            )

    def test_imported_static_method_owner_shadowed_by_primitive_parameter(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "dep/b.java": (
                        "package dep;\n"
                        "public class b {\n"
                        "    public static int a(int x) { return x + 1; }\n"
                        "    public static int b(int x) { return x + 2; }\n"
                        "}\n"
                    ),
                    "use/Current.java": (
                        "package use;\n"
                        "import dep.b;\n"
                        "public class Current {\n"
                        "    public static int m(boolean b) {\n"
                        "        return dep.b.a(1) + dep.b.b(2);\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )
            source = root / "src" / "use" / "Current.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package use;\n"
                "import dep.b;\n"
                "public class Current {\n"
                "    public static int m(boolean b) {\n"
                "        return b.a(1) + b.b(2);\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )

            before = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "before-imported-static-method-classes"),
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(before.returncode, 0)
            self.assertIn("boolean cannot be dereferenced", before.stderr)

            report = normalize_procyon_source(root / "src", jar)
            normalized = source.read_text(encoding="utf-8")

            self.assertIn(
                "return dep.b.a(1) + dep.b.b(2);",
                normalized,
            )
            action = next(
                row
                for row in report["actions"]
                if row["kind"]
                == "shadowed_imported_static_method_owner_qualification"
            )
            self.assertEqual(action["imported_owner"], "dep/b")
            self.assertTrue(action["primitive_parameter_shadow"])
            self.assertEqual(action["call_counts"], {"a": 1, "b": 1})
            self.assertEqual(action["replacement_count"], 2)
            self.assertEqual(
                report["summary"][
                    "shadowed_imported_static_method_reference_count"
                ],
                2,
            )

            after = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "after-imported-static-method-classes"),
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(
                after.returncode,
                0,
                after.stdout + after.stderr,
            )

    def test_imported_static_method_owner_shadowed_by_primitive_field(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "dep/b.java": (
                        "package dep;\n"
                        "public class b {\n"
                        "    public static int a(int x) { return x + 1; }\n"
                        "}\n"
                    ),
                    "use/Current.java": (
                        "package use;\n"
                        "import dep.b;\n"
                        "public class Current {\n"
                        "    public boolean b;\n"
                        "    public int m() {\n"
                        "        return (b ? 1 : 0) + dep.b.a(1);\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )
            source = root / "src" / "use" / "Current.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package use;\n"
                "import dep.b;\n"
                "public class Current {\n"
                "    public boolean b;\n"
                "    public int m() {\n"
                "        return (b ? 1 : 0) + b.a(1);\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )

            report = normalize_procyon_source(root / "src", jar)
            normalized = source.read_text(encoding="utf-8")

            self.assertIn(
                "return (b ? 1 : 0) + dep.b.a(1);",
                normalized,
            )
            action = next(
                row
                for row in report["actions"]
                if row["kind"]
                == "shadowed_imported_static_method_owner_qualification"
            )
            self.assertEqual(
                action["hierarchy_primitive_shadow_owner"],
                "use/Current",
            )
            self.assertEqual(action["replacement_count"], 1)

            after = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "after-imported-field-shadow-classes"),
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(
                after.returncode,
                0,
                after.stdout + after.stderr,
            )

    def test_imported_static_method_owner_count_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "dep/b.java": (
                        "package dep;\n"
                        "public class b {\n"
                        "    public static int a(int x) { return x + 1; }\n"
                        "}\n"
                    ),
                    "use/Current.java": (
                        "package use;\n"
                        "import dep.b;\n"
                        "public class Current {\n"
                        "    public static int m(boolean b) {\n"
                        "        return dep.b.a(1);\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )
            source = root / "src" / "use" / "Current.java"
            source.parent.mkdir(parents=True)
            original = (
                "package use;\n"
                "import dep.b;\n"
                "public class Current {\n"
                "    public static int m(boolean b) {\n"
                "        return b.a(1) + b.a(2);\n"
                "    }\n"
                "}\n"
            )
            source.write_text(original, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)

            self.assertEqual(source.read_text(encoding="utf-8"), original)
            self.assertEqual(
                report["summary"][
                    "shadowed_imported_static_method_reference_count"
                ],
                0,
            )

    def test_imported_static_field_shadow_in_static_method_forces_type_context(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "dep/E.java": (
                        "package dep;\n"
                        "public class E {\n"
                        "    public static int[] v = new int[] { 7 };\n"
                        "}\n"
                    ),
                    "use/Current.java": (
                        "package use;\n"
                        "import dep.E;\n"
                        "public class Current {\n"
                        "    public int[] E;\n"
                        "    public static int read() {\n"
                        "        return ((dep.E)null).v[0];\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )

            source = root / "src" / "use" / "Current.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package use;\n"
                "import dep.E;\n"
                "public class Current {\n"
                "    public int[] E;\n"
                "    public static int read() {\n"
                "        return E.v[0];\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )

            before = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "before-import-method-classes"),
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(before.returncode, 0)

            report = normalize_procyon_source(root / "src", jar)
            normalized = source.read_text(encoding="utf-8")

            self.assertIn("((dep.E)null).v[0]", normalized)
            action = next(
                row
                for row in report["actions"]
                if (
                    row["kind"]
                    == "shadowed_imported_static_field_owner_type_context"
                    and row.get("method_name") == "read"
                )
            )
            self.assertEqual(action["method_descriptor"], "()I")
            self.assertEqual(action["replacement_count"], 1)

            after = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "after-import-method-classes"),
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(
                after.returncode,
                0,
                after.stdout + after.stderr,
            )

    def test_imported_static_field_shadow_static_method_count_mismatch_fails_closed(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "dep/E.java": (
                        "package dep;\n"
                        "public class E { public static int v = 7; }\n"
                    ),
                    "use/Current.java": (
                        "package use;\n"
                        "import dep.E;\n"
                        "public class Current {\n"
                        "    public int E;\n"
                        "    public static int read() {\n"
                        "        return ((dep.E)null).v;\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )

            source = root / "src" / "use" / "Current.java"
            source.parent.mkdir(parents=True)
            original = (
                "package use;\n"
                "import dep.E;\n"
                "public class Current {\n"
                "    public int E;\n"
                "    public static int read() {\n"
                "        return E.v + E.v;\n"
                "    }\n"
                "}\n"
            )
            source.write_text(original, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)

            self.assertEqual(
                source.read_text(encoding="utf-8"),
                original,
            )
            self.assertFalse(
                any(
                    row["kind"]
                    == "shadowed_imported_static_field_owner_type_context"
                    and row.get("method_name") == "read"
                    for row in report["actions"]
                )
            )

    def test_imported_static_field_shadow_in_clinit_forces_type_context(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "dep/E.java": (
                        "package dep;\n"
                        "public class E {\n"
                        "    public static int v = 1;\n"
                        "    public static int w = 2;\n"
                        "}\n"
                    ),
                    "use/Current.java": (
                        "package use;\n"
                        "import dep.E;\n"
                        "public class Current {\n"
                        "    public int E;\n"
                        "    public static int value;\n"
                        "    static {\n"
                        "        value = ((dep.E)null).v"
                        " + ((dep.E)null).w;\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )

            source = root / "src" / "use" / "Current.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package use;\n"
                "import dep.E;\n"
                "public class Current {\n"
                "    public int E;\n"
                "    public static int value;\n"
                "    static {\n"
                "        value = E.v + E.w;\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )

            before = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "before-import-clinit-classes"),
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(before.returncode, 0)
            self.assertIn(
                "non-static variable E cannot be referenced",
                before.stderr,
            )

            report = normalize_procyon_source(root / "src", jar)
            normalized = source.read_text(encoding="utf-8")

            self.assertIn("((dep.E)null).v", normalized)
            self.assertIn("((dep.E)null).w", normalized)
            self.assertEqual(
                report["summary"][
                    "shadowed_imported_static_field_block_count"
                ],
                1,
            )
            self.assertEqual(
                report["summary"][
                    "shadowed_imported_static_field_reference_count"
                ],
                2,
            )

            action = next(
                row
                for row in report["actions"]
                if row["kind"]
                == "shadowed_imported_static_field_owner_type_context"
            )
            self.assertEqual(action["method_name"], "<clinit>")
            self.assertEqual(action["method_descriptor"], "()V")
            self.assertEqual(action["imported_owners"], ["dep/E"])
            self.assertEqual(action["replacement_count"], 2)

            after = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "after-import-clinit-classes"),
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(
                after.returncode,
                0,
                after.stdout + after.stderr,
            )

    def test_imported_static_field_shadow_in_clinit_count_mismatch_fails_closed(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "dep/E.java": (
                        "package dep;\n"
                        "public class E { public static int v = 1; }\n"
                    ),
                    "use/Current.java": (
                        "package use;\n"
                        "import dep.E;\n"
                        "public class Current {\n"
                        "    public int E;\n"
                        "    public static int value;\n"
                        "    static { value = ((dep.E)null).v; }\n"
                        "}\n"
                    ),
                },
            )

            source = root / "src" / "use" / "Current.java"
            source.parent.mkdir(parents=True)
            original = (
                "package use;\n"
                "import dep.E;\n"
                "public class Current {\n"
                "    public int E;\n"
                "    public static int value;\n"
                "    static { value = E.v + E.v; }\n"
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
                    "shadowed_imported_static_field_reference_count"
                ],
                0,
            )

    def test_invokedynamic_helper_return_cast_uses_generated_signature(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "p/Client.java": (
                        "package p;\n"
                        "public class Client {\n"
                        "    public static String concat(String p0) {\n"
                        "        return \"value=\" + p0;\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )
            source = root / "src" / "p" / "Client.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package p;\n"
                "public class Client {\n"
                "    public static String concat(String p0) {\n"
                "        return ProcyonInvokeDynamicHelper_1.invoke(p0);\n"
                "    }\n"
                "    private static final class ProcyonInvokeDynamicHelper_1 {\n"
                "        private static Handler handle() { return new Handler(); }\n"
                "        private static String invoke(String p0) {\n"
                "            return ProcyonInvokeDynamicHelper_1.handle().invokeExact(p0);\n"
                "        }\n"
                "        private static final class Handler {\n"
                "            Object invokeExact(Object value) { return value; }\n"
                "        }\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )

            before = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "before-invokedynamic-cast"),
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(before.returncode, 0)
            self.assertIn(
                "Object cannot be converted to String",
                before.stderr,
            )

            report = normalize_procyon_source(root / "src", jar)
            normalized = source.read_text(encoding="utf-8")

            self.assertIn(
                "return (java.lang.String)"
                "ProcyonInvokeDynamicHelper_1.handle().invokeExact(p0);",
                normalized,
            )
            action = next(
                row
                for row in report["actions"]
                if row["kind"] == "invokedynamic_helper_return_cast"
            )
            self.assertEqual(
                action["method_descriptor"],
                "(Ljava/lang/String;)Ljava/lang/String;",
            )
            self.assertEqual(
                action["helper_name"],
                "ProcyonInvokeDynamicHelper_1",
            )
            self.assertEqual(action["cast_type"], "java.lang.String")
            self.assertEqual(action["replacement_count"], 1)
            self.assertEqual(
                action["matching_invokedynamic_callsite_count"],
                1,
            )
            self.assertEqual(
                len(action["invokedynamic_callsites"]),
                1,
            )
            self.assertEqual(
                action["invokedynamic_callsites"][0]["descriptor"],
                "(Ljava/lang/String;)Ljava/lang/String;",
            )
            self.assertEqual(
                report["summary"][
                    "invokedynamic_helper_return_cast_reference_count"
                ],
                1,
            )

            after = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "after-invokedynamic-cast"),
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(
                after.returncode,
                0,
                after.stdout + after.stderr,
            )

    def test_invokedynamic_helper_descriptor_multiplicity_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "p/Client.java": (
                        "package p;\n"
                        "public class Client {\n"
                        "    public static String concat(String p0) {\n"
                        "        return \"value=\" + p0;\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )
            source = root / "src" / "p" / "Client.java"
            source.parent.mkdir(parents=True)
            original = (
                "package p;\n"
                "public class Client {\n"
                "    public static String concat(String p0) {\n"
                "        return ProcyonInvokeDynamicHelper_1.invoke(p0);\n"
                "    }\n"
                "    private static final class ProcyonInvokeDynamicHelper_1 {\n"
                "        private static Handler handle() { return new Handler(); }\n"
                "        private static String invoke(String p0) {\n"
                "            return ProcyonInvokeDynamicHelper_1.handle().invokeExact(p0);\n"
                "        }\n"
                "        private static final class Handler {\n"
                "            Object invokeExact(Object value) { return value; }\n"
                "        }\n"
                "    }\n"
                "    private static final class ProcyonInvokeDynamicHelper_2 {\n"
                "        private static Handler handle() { return new Handler(); }\n"
                "        private static String invoke(String p0) {\n"
                "            return ProcyonInvokeDynamicHelper_2.handle().invokeExact(p0);\n"
                "        }\n"
                "        private static final class Handler {\n"
                "            Object invokeExact(Object value) { return value; }\n"
                "        }\n"
                "    }\n"
                "}\n"
            )
            source.write_text(original, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)

            self.assertEqual(source.read_text(encoding="utf-8"), original)
            self.assertEqual(
                report["summary"][
                    "invokedynamic_helper_return_cast_reference_count"
                ],
                0,
            )

    def test_qualifies_imported_parameter_shadowed_by_same_package_type(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _import_shadow_parameter_fixture(
                root,
                descriptor_owner="imported",
            )
            source_root = root / "src"
            current = source_root / "p" / "Current.java"
            local = source_root / "p" / "h.java"
            current.parent.mkdir(parents=True)
            current.write_text(
                "package p;\n"
                "import other.h;\n"
                "public class Current {\n"
                "    public static void m(final h h, final int n) {\n"
                "        if (h != null) { h.a(n, new int[] { 1 }); }\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )
            local.write_text(
                "package p;\n"
                "public class h {\n"
                "    public void a(final Object value) {}\n"
                "    public int a(final int x, final int y, final int z) {\n"
                "        return x + y + z;\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )

            self.assertIn(
                "m(final h h, final int n)",
                current.read_text(encoding="utf-8"),
            )

            report = normalize_procyon_source(source_root, jar)
            normalized = current.read_text(encoding="utf-8")

            self.assertIn(
                "m(final other.h h, final int n)",
                normalized,
            )
            self.assertEqual(
                report["summary"]["imported_parameter_shadow_method_count"],
                1,
            )
            self.assertEqual(
                report["summary"][
                    "imported_parameter_shadow_reference_count"
                ],
                1,
            )
            action = next(
                row
                for row in report["actions"]
                if row["kind"]
                == "imported_parameter_type_shadowed_by_same_package"
            )
            self.assertEqual(
                action["method_descriptor"],
                "(Lother/h;I)V",
            )
            self.assertEqual(
                action["replacements"],
                [
                    {
                        "parameter_index": 0,
                        "simple_name": "h",
                        "imported_owner": "other/h",
                        "same_package_owner": "p/h",
                        "qualified_type": "other.h",
                    }
                ],
            )

            after = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "after-classes"),
                    str(current),
                    str(local),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(
                after.returncode,
                0,
                after.stdout + after.stderr,
            )

    def test_imported_parameter_shadow_fails_closed_for_same_package_descriptor(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _import_shadow_parameter_fixture(
                root,
                descriptor_owner="same_package",
            )
            source_root = root / "src"
            current = source_root / "p" / "Current.java"
            local = source_root / "p" / "h.java"
            current.parent.mkdir(parents=True)
            original = (
                "package p;\n"
                "import other.h;\n"
                "public class Current {\n"
                "    public static void m(final h h, final int n) {\n"
                "        if (h != null) { h.a(Integer.valueOf(n)); }\n"
                "    }\n"
                "}\n"
            )
            current.write_text(original, encoding="utf-8")
            local.write_text(
                "package p;\n"
                "public class h {\n"
                "    public void a(final Object value) {}\n"
                "}\n",
                encoding="utf-8",
            )

            report = normalize_procyon_source(source_root, jar)

            self.assertEqual(
                current.read_text(encoding="utf-8"),
                original,
            )
            self.assertEqual(
                report["summary"][
                    "imported_parameter_shadow_reference_count"
                ],
                0,
            )

    def test_same_package_static_method_owner_shadowed_by_reference_parameter(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "p/s.java": (
                        "package p;\n"
                        "public class s {\n"
                        "    public static int a() { return 1; }\n"
                        "    public static int a(String s, int i) { return i; }\n"
                        "    public static int a(String s, int i, int n) { return i + n; }\n"
                        "    public static int b() { return 2; }\n"
                        "    public static int b(String s, int i, int n) { return i - n; }\n"
                        "    public static void c() {}\n"
                        "}\n"
                    ),
                    "p/h.java": (
                        "package p;\n"
                        "public class h {\n"
                        "    public int m(String s, int i, int n) {\n"
                        "        int x = p.s.a(s, i);\n"
                        "        x += p.s.a(s, i, n);\n"
                        "        x += p.s.b(s, i, n);\n"
                        "        x += p.s.b() + p.s.a();\n"
                        "        p.s.c();\n"
                        "        return x;\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )
            source = root / "src" / "p" / "h.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package p;\n"
                "public class h {\n"
                "    public int m(String s, int i, int n) {\n"
                "        int x = s.a(s, i);\n"
                "        x += s.a(s, i, n);\n"
                "        x += s.b(s, i, n);\n"
                "        x += s.b() + s.a();\n"
                "        s.c();\n"
                "        return x;\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )

            before = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "before-same-package-call-ref"),
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(before.returncode, 0)
            self.assertIn("cannot find symbol", before.stderr)

            report = normalize_procyon_source(root / "src", jar)
            normalized = source.read_text(encoding="utf-8")

            self.assertIn("int x = p.s.a(s, i);", normalized)
            self.assertIn("x += p.s.a(s, i, n);", normalized)
            self.assertIn("x += p.s.b(s, i, n);", normalized)
            self.assertIn("x += p.s.b() + p.s.a();", normalized)
            self.assertIn("p.s.c();", normalized)

            action = next(
                row
                for row in report["actions"]
                if row["kind"]
                == "shadowed_same_package_static_method_owner_qualification"
            )
            self.assertEqual(action["same_package_owner"], "p/s")
            self.assertTrue(action["reference_parameter_shadow"])
            self.assertEqual(action["replacement_count"], 6)
            self.assertEqual(
                action["call_counts"],
                {"a": 3, "b": 2, "c": 1},
            )
            self.assertEqual(
                report["summary"][
                    "shadowed_same_package_static_method_reference_count"
                ],
                6,
            )

            after = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "after-same-package-call-ref"),
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(
                after.returncode,
                0,
                after.stdout + after.stderr,
            )

    def test_same_package_static_method_owner_shadowed_by_primitive_parameter(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "p/n.java": (
                        "package p;\n"
                        "public class n {\n"
                        "    public static int a(int x) { return x + 1; }\n"
                        "}\n"
                    ),
                    "p/h.java": (
                        "package p;\n"
                        "public class h {\n"
                        "    public int m(int n) { return p.n.a(n); }\n"
                        "}\n"
                    ),
                },
            )
            source = root / "src" / "p" / "h.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package p;\n"
                "public class h {\n"
                "    public int m(int n) { return n.a(n); }\n"
                "}\n",
                encoding="utf-8",
            )

            report = normalize_procyon_source(root / "src", jar)
            normalized = source.read_text(encoding="utf-8")

            self.assertIn("return p.n.a(n);", normalized)
            action = next(
                row
                for row in report["actions"]
                if row["kind"]
                == "shadowed_same_package_static_method_owner_qualification"
            )
            self.assertTrue(action["primitive_parameter_shadow"])
            self.assertEqual(action["replacement_count"], 1)

            after = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "after-same-package-call-primitive"),
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(
                after.returncode,
                0,
                after.stdout + after.stderr,
            )

    def test_same_package_static_method_owner_count_mismatch_fails_closed(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "p/s.java": (
                        "package p;\n"
                        "public class s {\n"
                        "    public static int a(String s) { return 1; }\n"
                        "}\n"
                    ),
                    "p/h.java": (
                        "package p;\n"
                        "public class h {\n"
                        "    public int m(String s) { return p.s.a(s); }\n"
                        "}\n"
                    ),
                },
            )
            source = root / "src" / "p" / "h.java"
            source.parent.mkdir(parents=True)
            original = (
                "package p;\n"
                "public class h {\n"
                "    public int m(String s) {\n"
                "        return s.a(s) + s.a(s);\n"
                "    }\n"
                "}\n"
            )
            source.write_text(original, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)

            self.assertEqual(source.read_text(encoding="utf-8"), original)
            self.assertEqual(
                report["summary"][
                    "shadowed_same_package_static_method_reference_count"
                ],
                0,
            )

    def test_scoped_same_package_static_fields_shadowed_by_reference_parameter(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "p/b.java": (
                        "package p;\n"
                        "public class b {\n"
                        "    public static int j = 7;\n"
                        "    public static int f = 9;\n"
                        "}\n"
                    ),
                    "p/Ref.java": (
                        "package p;\n"
                        "public class Ref {}\n"
                    ),
                    "p/a.java": (
                        "package p;\n"
                        "public class a {\n"
                        "    public int m(Ref b) {\n"
                        "        return p.b.j + p.b.f;\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )
            source = root / "src" / "p" / "a.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package p;\n"
                "public class a {\n"
                "    public int m(Ref b) {\n"
                "        return b.j + b.f;\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )

            before = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "before-scoped-same-package-field"),
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(before.returncode, 0)
            self.assertIn("cannot find symbol", before.stderr)

            report = normalize_procyon_source(root / "src", jar)
            normalized = source.read_text(encoding="utf-8")

            self.assertIn("((p.b)null).j", normalized)
            self.assertIn("((p.b)null).f", normalized)
            action = next(
                row
                for row in report["actions"]
                if row["kind"]
                == "scoped_same_package_static_field_owner_qualification"
            )
            self.assertEqual(action["same_package_owner"], "p/b")
            self.assertTrue(action["reference_parameter_shadow"])
            self.assertEqual(action["replacement_count"], 2)
            self.assertEqual(
                action["field_access_counts"],
                {"f": 1, "j": 1},
            )
            self.assertEqual(
                report["summary"][
                    "scoped_same_package_static_field_reference_count"
                ],
                2,
            )

            after = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "after-scoped-same-package-field"),
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(
                after.returncode,
                0,
                after.stdout + after.stderr,
            )

    def test_scoped_same_package_static_field_count_mismatch_fails_closed(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "p/b.java": (
                        "package p;\n"
                        "public class b { public static int j = 7; }\n"
                    ),
                    "p/Ref.java": (
                        "package p;\n"
                        "public class Ref {}\n"
                    ),
                    "p/a.java": (
                        "package p;\n"
                        "public class a {\n"
                        "    public int m(Ref b) { return p.b.j; }\n"
                        "}\n"
                    ),
                },
            )
            source = root / "src" / "p" / "a.java"
            source.parent.mkdir(parents=True)
            original = (
                "package p;\n"
                "public class a {\n"
                "    public int m(Ref b) { return b.j + b.j; }\n"
                "}\n"
            )
            source.write_text(original, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)

            self.assertEqual(source.read_text(encoding="utf-8"), original)
            self.assertEqual(
                report["summary"][
                    "scoped_same_package_static_field_reference_count"
                ],
                0,
            )

    def test_same_package_static_field_shadow_in_static_method_forces_type_context(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "p/i.java": (
                        "package p;\n"
                        "public class i {\n"
                        "    public static final i a = new i();\n"
                        "}\n"
                    ),
                    "p/f.java": (
                        "package p;\n"
                        "public class f {\n"
                        "    public static float a = 0.5f;\n"
                        "}\n"
                    ),
                    "p/g.java": (
                        "package p;\n"
                        "public class g {\n"
                        "    public i f;\n"
                        "    public float i;\n"
                        "    public static float read() {\n"
                        "        return ((p.f)null).a"
                        " + (((p.i)null).a == null ? 0.0f : 1.0f);\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )

            source = root / "src" / "p" / "g.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package p;\n"
                "public class g {\n"
                "    public i f;\n"
                "    public float i;\n"
                "    public static float read() {\n"
                "        return f.a + (i.a == null ? 0.0f : 1.0f);\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )

            before = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "before-same-package-owner-classes"),
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(before.returncode, 0)

            report = normalize_procyon_source(root / "src", jar)
            normalized = source.read_text(encoding="utf-8")

            self.assertIn("((p.f)null).a", normalized)
            self.assertIn("((p.i)null).a", normalized)

            action = next(
                row
                for row in report["actions"]
                if row["kind"]
                == "shadowed_same_package_static_field_owner_type_context"
            )
            self.assertEqual(action["method_name"], "read")
            self.assertEqual(action["method_descriptor"], "()F")
            self.assertEqual(
                action["same_package_owners"],
                ["p/f", "p/i"],
            )
            self.assertEqual(
                action["field_access_counts"],
                {
                    "p/f.a": 1,
                    "p/i.a": 1,
                },
            )
            self.assertEqual(action["replacement_count"], 2)
            self.assertEqual(
                report["summary"][
                    "shadowed_same_package_static_field_method_count"
                ],
                1,
            )
            self.assertEqual(
                report["summary"][
                    "shadowed_same_package_static_field_reference_count"
                ],
                2,
            )

            after = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "after-same-package-owner-classes"),
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(
                after.returncode,
                0,
                after.stdout + after.stderr,
            )

    def test_same_package_static_field_shadow_in_instance_method_forces_type_context(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "p/b.java": (
                        "package p;\n"
                        "public class b {\n"
                        "    public static int j = 7;\n"
                        "    public static int f = 9;\n"
                        "}\n"
                    ),
                    "p/Ref.java": (
                        "package p;\n"
                        "public class Ref {}\n"
                    ),
                    "p/a.java": (
                        "package p;\n"
                        "public class a {\n"
                        "    public Ref b;\n"
                        "    public int read() {\n"
                        "        return ((p.b)null).j + ((p.b)null).f;\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )

            source = root / "src" / "p" / "a.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package p;\n"
                "public class a {\n"
                "    public Ref b;\n"
                "    public int read() {\n"
                "        return b.j + b.f;\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )

            before = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "before-instance-owner-classes"),
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(before.returncode, 0)
            self.assertIn("cannot find symbol", before.stderr)

            report = normalize_procyon_source(root / "src", jar)
            normalized = source.read_text(encoding="utf-8")

            self.assertIn("((p.b)null).j", normalized)
            self.assertIn("((p.b)null).f", normalized)

            action = next(
                row
                for row in report["actions"]
                if row["kind"]
                == "shadowed_same_package_static_field_owner_type_context"
            )
            self.assertEqual(action["method_name"], "read")
            self.assertEqual(action["method_descriptor"], "()I")
            self.assertEqual(action["same_package_owners"], ["p/b"])
            self.assertEqual(
                action["field_access_counts"],
                {"p/b.f": 1, "p/b.j": 1},
            )
            self.assertEqual(action["replacement_count"], 2)

            after = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "after-instance-owner-classes"),
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(
                after.returncode,
                0,
                after.stdout + after.stderr,
            )

    def test_same_package_static_field_shadow_count_mismatch_fails_closed(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "p/f.java": (
                        "package p;\n"
                        "public class f {\n"
                        "    public static float a = 0.5f;\n"
                        "}\n"
                    ),
                    "p/g.java": (
                        "package p;\n"
                        "public class g {\n"
                        "    public Object f;\n"
                        "    public static float read() {\n"
                        "        return ((p.f)null).a;\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )

            source = root / "src" / "p" / "g.java"
            source.parent.mkdir(parents=True)
            original = (
                "package p;\n"
                "public class g {\n"
                "    public Object f;\n"
                "    public static float read() {\n"
                "        return f.a + f.a;\n"
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
                    "shadowed_same_package_static_field_reference_count"
                ],
                0,
            )
            self.assertFalse(
                any(
                    row["kind"]
                    == "shadowed_same_package_static_field_owner_type_context"
                    for row in report["actions"]
                )
            )

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


    def test_simple_nested_static_owner_shadowed_by_hierarchy_field(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "p/Base.java": (
                        "package p;\n"
                        "public class Base {\n"
                        "    public Object b;\n"
                        "    public long c;\n"
                        "}\n"
                    ),
                    "p/Outer.java": (
                        "package p;\n"
                        "public class Outer extends Base {\n"
                        "    public static class b {\n"
                        "        public static int j = 7;\n"
                        "        public static int f = 9;\n"
                        "    }\n"
                        "    public static class c {\n"
                        "        public static final c a = new c();\n"
                        "    }\n"
                        "    public int read() {\n"
                        "        return ((p.Outer.b)null).j"
                        " + ((p.Outer.b)null).f"
                        " + (((p.Outer.c)null).a == null ? 0 : 1);\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )

            source = root / "src" / "p" / "Outer.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package p;\n"
                "public class Outer extends Base {\n"
                "    public static class b {\n"
                "        public static int j = 7;\n"
                "        public static int f = 9;\n"
                "    }\n"
                "    public static class c {\n"
                "        public static final c a = new c();\n"
                "    }\n"
                "    public int read() {\n"
                "        return b.j + b.f + (c.a == null ? 0 : 1);\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )

            before = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "before-simple-nested"),
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(before.returncode, 0)

            report = normalize_procyon_source(root / "src", jar)
            normalized = source.read_text(encoding="utf-8")

            self.assertIn("((p.Outer.b)null).j", normalized)
            self.assertIn("((p.Outer.b)null).f", normalized)
            self.assertIn("((p.Outer.c)null).a", normalized)

            action = next(
                row
                for row in report["actions"]
                if (
                    row["kind"]
                    == "shadowed_nested_static_field_owner_type_context"
                    and row["method_name"] == "read"
                )
            )
            self.assertEqual(action["method_descriptor"], "()I")
            self.assertEqual(
                action["nested_owners"],
                ["p/Outer$b", "p/Outer$c"],
            )
            self.assertEqual(action["replacement_count"], 3)
            self.assertEqual(
                action["field_access_counts"],
                {
                    "p/Outer$b.f": 1,
                    "p/Outer$b.j": 1,
                    "p/Outer$c.a": 1,
                },
            )

            after = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "after-simple-nested"),
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(after.returncode, 0, after.stdout + after.stderr)

    def test_simple_nested_private_static_owner_shadowed_by_hierarchy_field(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "p/Base.java": (
                        "package p;\n"
                        "public class Base { public Object b; }\n"
                    ),
                    "p/Outer.java": (
                        "package p;\n"
                        "public class Outer extends Base {\n"
                        "    public static class b {\n"
                        "        private static int j = 7;\n"
                        "        private static int f = 9;\n"
                        "    }\n"
                        "    public int read() {\n"
                        "        return ((p.Outer.b)null).j"
                        " + ((p.Outer.b)null).f;\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )

            source = root / "src" / "p" / "Outer.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package p;\n"
                "public class Outer extends Base {\n"
                "    public static class b {\n"
                "        private static int j = 7;\n"
                "        private static int f = 9;\n"
                "    }\n"
                "    public int read() { return b.j + b.f; }\n"
                "}\n",
                encoding="utf-8",
            )

            before = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "before-private-simple-nested"),
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(before.returncode, 0)

            report = normalize_procyon_source(root / "src", jar)
            normalized = source.read_text(encoding="utf-8")

            self.assertIn("((p.Outer.b)null).j", normalized)
            self.assertIn("((p.Outer.b)null).f", normalized)
            action = next(
                row
                for row in report["actions"]
                if (
                    row["kind"]
                    == "shadowed_nested_static_field_owner_type_context"
                    and row["method_name"] == "read"
                )
            )
            self.assertEqual(action["nested_owners"], ["p/Outer$b"])
            self.assertEqual(
                action["field_access_counts"],
                {"p/Outer$b.f": 1, "p/Outer$b.j": 1},
            )
            self.assertEqual(action["replacement_count"], 2)

            after = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "after-private-simple-nested"),
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(after.returncode, 0, after.stdout + after.stderr)

    def test_scoped_same_package_static_field_with_hierarchy_name_collision(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "p/b.java": (
                        "package p;\n"
                        "public class b { public static int a = 7; }\n"
                    ),
                    "p/Ref.java": (
                        "package p;\n"
                        "public class Ref { public int s = 3; }\n"
                    ),
                    "p/Base.java": (
                        "package p;\n"
                        "public class Base { public Ref b; }\n"
                    ),
                    "p/A.java": (
                        "package p;\n"
                        "public class A extends Base {\n"
                        "    public int m(Ref b) {\n"
                        "        return ((p.b)null).a + b.s;\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )

            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package p;\n"
                "public class A extends Base {\n"
                "    public int m(Ref b) {\n"
                "        return b.a + b.s;\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )

            before = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "before-mixed-same-package"),
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(before.returncode, 0)
            self.assertIn("cannot find symbol", before.stderr)

            report = normalize_procyon_source(root / "src", jar)
            normalized = source.read_text(encoding="utf-8")

            self.assertIn("return ((p.b)null).a + b.s;", normalized)
            action = next(
                row
                for row in report["actions"]
                if row["kind"]
                == "scoped_same_package_static_field_owner_qualification"
            )
            self.assertEqual(action["same_package_owner"], "p/b")
            self.assertTrue(action["reference_parameter_shadow"])
            self.assertEqual(action["field_access_counts"], {"a": 1})
            self.assertEqual(action["replacement_count"], 1)

            after = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "after-mixed-same-package"),
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(after.returncode, 0, after.stdout + after.stderr)


    def test_undeclared_linkedhashmap_non_result_placeholders_become_wildcards(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "p/Value.java": (
                        "package p;\n"
                        "public class Value {}\n"
                    ),
                    "p/A.java": (
                        "package p;\n"
                        "import java.util.LinkedHashMap;\n"
                        "import java.util.Set;\n"
                        "public class A extends LinkedHashMap<String, Value> {\n"
                        "    public Value byKey(String key) {\n"
                        "        return this.get(key);\n"
                        "    }\n"
                        "    public Set<String> keys() {\n"
                        "        return this.keySet();\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )

            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package p;\n"
                "import java.util.LinkedHashMap;\n"
                "import java.util.Set;\n"
                "public class A extends LinkedHashMap<String, Value> {\n"
                "    public Value byKey(String key) {\n"
                "        return ((LinkedHashMap<K, Value>)this).get(key);\n"
                "    }\n"
                "    public Set<String> keys() {\n"
                "        return ((LinkedHashMap<String, V>)this).keySet();\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )

            before = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "before-linkedhashmap-placeholder"),
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(before.returncode, 0)
            self.assertIn("cannot find symbol", before.stderr)

            report = normalize_procyon_source(root / "src", jar)
            normalized = source.read_text(encoding="utf-8")

            self.assertIn(
                "((LinkedHashMap<?, Value>)this).get(key)",
                normalized,
            )
            self.assertIn(
                "((LinkedHashMap<String, ?>)this).keySet()",
                normalized,
            )
            actions = [
                row
                for row in report["actions"]
                if row["kind"]
                == "undeclared_linkedhashmap_cast_placeholder_wildcard"
            ]
            self.assertEqual(len(actions), 2)
            by_name = {row["method_name"]: row for row in actions}
            self.assertEqual(
                by_name["byKey"]["method_descriptor"],
                "(Ljava/lang/String;)Lp/Value;",
            )
            self.assertEqual(
                by_name["byKey"]["placeholder_counts"],
                {"K": 1},
            )
            self.assertEqual(
                by_name["byKey"]["member_counts"],
                {"get": 1},
            )
            self.assertEqual(
                by_name["keys"]["method_descriptor"],
                "()Ljava/util/Set;",
            )
            self.assertEqual(
                by_name["keys"]["placeholder_counts"],
                {"V": 1},
            )
            self.assertEqual(
                by_name["keys"]["member_counts"],
                {"keySet": 1},
            )
            self.assertEqual(
                report["summary"][
                    "undeclared_linkedhashmap_cast_placeholder_method_count"
                ],
                2,
            )
            self.assertEqual(
                report["summary"][
                    "undeclared_linkedhashmap_cast_placeholder_reference_count"
                ],
                2,
            )

            after = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "after-linkedhashmap-placeholder"),
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(after.returncode, 0, after.stdout + after.stderr)

    def test_linkedhashmap_placeholder_rule_preserves_declared_type_parameters(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "p/Value.java": (
                        "package p;\n"
                        "public class Value {}\n"
                    ),
                    "p/A.java": (
                        "package p;\n"
                        "import java.util.LinkedHashMap;\n"
                        "public class A<K, V> "
                        "extends LinkedHashMap<String, Value> {\n"
                        "    public Value byKey(String key) {\n"
                        "        return this.get(key);\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )

            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            original = (
                "package p;\n"
                "import java.util.LinkedHashMap;\n"
                "public class A<K, V> "
                "extends LinkedHashMap<String, Value> {\n"
                "    public Value byKey(String key) {\n"
                "        return ((LinkedHashMap<K, Value>)this).get(key);\n"
                "    }\n"
                "}\n"
            )
            source.write_text(original, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)

            self.assertEqual(source.read_text(encoding="utf-8"), original)
            self.assertEqual(
                report["summary"][
                    "undeclared_linkedhashmap_cast_placeholder_reference_count"
                ],
                0,
            )

    def test_linkedhashmap_placeholder_rule_does_not_erase_result_type(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "p/Value.java": (
                        "package p;\n"
                        "public class Value {}\n"
                    ),
                    "p/A.java": (
                        "package p;\n"
                        "import java.util.LinkedHashMap;\n"
                        "public class A extends "
                        "LinkedHashMap<String, Value> {\n"
                        "    public Value byKey(String key) {\n"
                        "        return this.get(key);\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )

            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            original = (
                "package p;\n"
                "import java.util.LinkedHashMap;\n"
                "public class A extends LinkedHashMap<String, Value> {\n"
                "    public Value byKey(String key) {\n"
                "        return ((LinkedHashMap<String, V>)this).get(key);\n"
                "    }\n"
                "}\n"
            )
            source.write_text(original, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)

            self.assertEqual(source.read_text(encoding="utf-8"), original)
            self.assertEqual(
                report["summary"][
                    "undeclared_linkedhashmap_cast_placeholder_reference_count"
                ],
                0,
            )


if __name__ == "__main__":
    unittest.main()

# R8M exact-v308 acceptance is recorded on PR #114; keep this test surface CI-bound.

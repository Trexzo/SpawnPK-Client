from __future__ import annotations

import struct
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock
import zipfile

from spk_recovery.bytecode_profile import (
    profile_class_field_accesses as profile_class_field_accesses_exact,
)
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

    def test_imported_static_method_owner_shadowed_by_reference_field(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "dep/r.java": (
                        "package dep;\n"
                        "public class r {\n"
                        "    public static r c(int x) { return new r(); }\n"
                        "}\n"
                    ),
                    "use/Current.java": (
                        "package use;\n"
                        "import dep.r;\n"
                        "public class Current {\n"
                        "    public byte[][][] r;\n"
                        "    public r m(int n) {\n"
                        "        return dep.r.c(n);\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )
            source = root / "src" / "use" / "Current.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package use;\n"
                "import dep.r;\n"
                "public class Current {\n"
                "    public byte[][][] r;\n"
                "    public r m(int n) {\n"
                "        return r.c(n);\n"
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
                    str(root / "before-imported-reference-field"),
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(before.returncode, 0)

            report = normalize_procyon_source(root / "src", jar)
            normalized = source.read_text(encoding="utf-8")
            self.assertIn("return dep.r.c(n);", normalized)

            action = next(
                row
                for row in report["actions"]
                if row["kind"]
                == "shadowed_imported_static_method_owner_qualification"
            )
            self.assertEqual(action["hierarchy_shadow_owner"], "use/Current")
            self.assertIsNone(
                action["hierarchy_primitive_shadow_owner"]
            )
            self.assertEqual(action["replacement_count"], 1)

            after = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "after-imported-reference-field"),
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

    def test_imported_static_method_owner_shadowed_by_reference_parameter(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "dep/r.java": (
                        "package dep;\n"
                        "public class r {\n"
                        "    public static int c(int x) { return x + 1; }\n"
                        "}\n"
                    ),
                    "use/Current.java": (
                        "package use;\n"
                        "import dep.r;\n"
                        "public class Current {\n"
                        "    public static int m(byte[] r, int n) {\n"
                        "        return dep.r.c(n);\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )
            source = root / "src" / "use" / "Current.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package use;\n"
                "import dep.r;\n"
                "public class Current {\n"
                "    public static int m(byte[] r, int n) {\n"
                "        return r.c(n);\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )

            report = normalize_procyon_source(root / "src", jar)
            normalized = source.read_text(encoding="utf-8")
            self.assertIn("return dep.r.c(n);", normalized)

            action = next(
                row
                for row in report["actions"]
                if row["kind"]
                == "shadowed_imported_static_method_owner_qualification"
            )
            self.assertTrue(action["reference_parameter_shadow"])
            self.assertEqual(action["replacement_count"], 1)

    def test_imported_static_method_owner_shadowed_by_reference_local_scope(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "dep/r.java": (
                        "package dep;\n"
                        "public class r {\n"
                        "    public static int c(int x) { return x + 1; }\n"
                        "}\n"
                    ),
                    "use/Current.java": (
                        "package use;\n"
                        "import dep.r;\n"
                        "public class Current {\n"
                        "    public static int m(int n) {\n"
                        "        { byte[] r = null; return dep.r.c(n); }\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )
            source = root / "src" / "use" / "Current.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package use;\n"
                "import dep.r;\n"
                "public class Current {\n"
                "    public static int m(int n) {\n"
                "        { byte[] r = null; return r.c(n); }\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )

            report = normalize_procyon_source(root / "src", jar)
            normalized = source.read_text(encoding="utf-8")
            self.assertIn("return dep.r.c(n);", normalized)

            action = next(
                row
                for row in report["actions"]
                if row["kind"]
                == "shadowed_imported_static_method_owner_qualification"
            )
            self.assertEqual(
                action["reference_local_shadow_scope_count"],
                1,
            )
            self.assertEqual(action["replacement_count"], 1)

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

    def test_compile_time_lombok_nonnull_is_erased_with_exact_metadata(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "lombok/NonNull.java": (
                        "package lombok;\n"
                        "import java.lang.annotation.ElementType;\n"
                        "import java.lang.annotation.Retention;\n"
                        "import java.lang.annotation.RetentionPolicy;\n"
                        "import java.lang.annotation.Target;\n"
                        "@Retention(RetentionPolicy.CLASS)\n"
                        "@Target({ElementType.PARAMETER, ElementType.TYPE_USE, ElementType.METHOD})\n"
                        "public @interface NonNull {}\n"
                    ),
                    "p/A.java": (
                        "package p;\n"
                        "import lombok.NonNull;\n"
                        "public class A {\n"
                        "    public static String value(@NonNull String value) {\n"
                        "        if (value == null) {\n"
                        "            throw new NullPointerException(\"value is marked non-null but is null\");\n"
                        "        }\n"
                        "        return value;\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package p;\n"
                "import lombok.NonNull;\n"
                "public class A {\n"
                "    public static String value(@NonNull String value) {\n"
                "        if (value == null) {\n"
                "            throw new NullPointerException(\"value is marked non-null but is null\");\n"
                "        }\n"
                "        return value;\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )

            before = subprocess.run(
                [
                    "javac",
                    "-d",
                    str(root / "before-lombok-erasure"),
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(before.returncode, 0)
            self.assertIn("lombok", before.stderr)

            report = normalize_procyon_source(root / "src", jar)
            normalized = source.read_text(encoding="utf-8")
            self.assertNotIn("import lombok.NonNull;", normalized)
            self.assertNotIn("@NonNull", normalized)
            self.assertIn(
                'throw new NullPointerException("value is marked non-null but is null");',
                normalized,
            )

            action = next(
                row
                for row in report["actions"]
                if row["kind"] == "compile_time_lombok_nonnull_erasure"
            )
            self.assertEqual(action["replacement_count"], 1)
            self.assertEqual(action["removed_import_count"], 1)
            self.assertEqual(
                report["summary"][
                    "compile_time_lombok_nonnull_reference_count"
                ],
                1,
            )

            after = subprocess.run(
                [
                    "javac",
                    "-d",
                    str(root / "after-lombok-erasure"),
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

    def test_compile_time_lombok_nonnull_keeps_real_class_reference(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "lombok/NonNull.java": (
                        "package lombok;\n"
                        "import java.lang.annotation.ElementType;\n"
                        "import java.lang.annotation.Retention;\n"
                        "import java.lang.annotation.RetentionPolicy;\n"
                        "import java.lang.annotation.Target;\n"
                        "@Retention(RetentionPolicy.CLASS)\n"
                        "@Target({ElementType.PARAMETER, ElementType.TYPE_USE})\n"
                        "public @interface NonNull {}\n"
                    ),
                    "p/A.java": (
                        "package p;\n"
                        "import lombok.NonNull;\n"
                        "public class A {\n"
                        "    public static Class<?> type(@NonNull String value) {\n"
                        "        return NonNull.class;\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            original = (
                "package p;\n"
                "import lombok.NonNull;\n"
                "public class A {\n"
                "    public static Class<?> type(@NonNull String value) {\n"
                "        return NonNull.class;\n"
                "    }\n"
                "}\n"
            )
            source.write_text(original, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)

            self.assertEqual(source.read_text(encoding="utf-8"), original)
            self.assertEqual(
                report["summary"][
                    "compile_time_lombok_nonnull_reference_count"
                ],
                0,
            )

    def test_two_string_swing_capture_aliases_use_exact_slot_order(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "p/Client.java": (
                        "package p;\n"
                        "import java.awt.Toolkit;\n"
                        "import java.awt.datatransfer.StringSelection;\n"
                        "import javax.swing.JOptionPane;\n"
                        "import javax.swing.SwingUtilities;\n"
                        "public class Client {\n"
                        "    private static void show(String first, String second) {\n"
                        "        SwingUtilities.invokeLater(() -> {\n"
                        "            if (JOptionPane.showConfirmDialog(null, first, \"Message\", 2) == 0) {\n"
                        "                Toolkit.getDefaultToolkit().getSystemClipboard().setContents(new StringSelection(second), null);\n"
                        "            }\n"
                        "        });\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )
            source = root / "src" / "p" / "Client.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package p;\n"
                "import java.awt.Toolkit;\n"
                "import java.awt.datatransfer.StringSelection;\n"
                "import javax.swing.JOptionPane;\n"
                "import javax.swing.SwingUtilities;\n"
                "public class Client {\n"
                "    private static void show(String s, String s2) {\n"
                "        SwingUtilities.invokeLater(() -> {\n"
                "            if (JOptionPane.showConfirmDialog(null, message, \"Message\", 2) == 0) {\n"
                "                Toolkit.getDefaultToolkit().getSystemClipboard().setContents(new StringSelection(data), null);\n"
                "            }\n"
                "        });\n"
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
                    str(root / "before-two-string-swing"),
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
                'showConfirmDialog(null, s, "Message", 2)',
                normalized,
            )
            self.assertIn("new StringSelection(s2)", normalized)
            self.assertNotIn("message", normalized)
            self.assertNotIn("data)", normalized)

            action = next(
                row
                for row in report["actions"]
                if row["kind"] == "two_string_swing_capture_alias"
            )
            self.assertEqual(action["message_parameter_name"], "s")
            self.assertEqual(action["data_parameter_name"], "s2")
            self.assertEqual(action["message_alias_name"], "message")
            self.assertEqual(action["data_alias_name"], "data")
            self.assertEqual(action["replacement_count"], 2)
            self.assertEqual(
                report["summary"][
                    "two_string_swing_capture_alias_reference_count"
                ],
                2,
            )

            after = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "after-two-string-swing"),
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

    def test_two_string_swing_capture_aliases_require_exact_slot_use(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "p/Client.java": (
                        "package p;\n"
                        "import java.awt.Toolkit;\n"
                        "import java.awt.datatransfer.StringSelection;\n"
                        "import javax.swing.JOptionPane;\n"
                        "import javax.swing.SwingUtilities;\n"
                        "public class Client {\n"
                        "    private static void show(String first, String second) {\n"
                        "        SwingUtilities.invokeLater(() -> {\n"
                        "            if (JOptionPane.showConfirmDialog(null, second, \"Message\", 2) == 0) {\n"
                        "                Toolkit.getDefaultToolkit().getSystemClipboard().setContents(new StringSelection(first), null);\n"
                        "            }\n"
                        "        });\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )
            source = root / "src" / "p" / "Client.java"
            source.parent.mkdir(parents=True)
            original = (
                "package p;\n"
                "import java.awt.Toolkit;\n"
                "import java.awt.datatransfer.StringSelection;\n"
                "import javax.swing.JOptionPane;\n"
                "import javax.swing.SwingUtilities;\n"
                "public class Client {\n"
                "    private static void show(String s, String s2) {\n"
                "        SwingUtilities.invokeLater(() -> {\n"
                "            if (JOptionPane.showConfirmDialog(null, message, \"Message\", 2) == 0) {\n"
                "                Toolkit.getDefaultToolkit().getSystemClipboard().setContents(new StringSelection(data), null);\n"
                "            }\n"
                "        });\n"
                "    }\n"
                "}\n"
            )
            source.write_text(original, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)

            self.assertEqual(source.read_text(encoding="utf-8"), original)
            self.assertEqual(
                report["summary"][
                    "two_string_swing_capture_alias_reference_count"
                ],
                0,
            )

    def test_invokedynamic_parameter_capture_alias_uses_exact_callsite(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "p/Event.java": (
                        "package p;\n"
                        "public interface Event { void touch(); }\n"
                    ),
                    "p/Client.java": (
                        "package p;\n"
                        "public class Client {\n"
                        "    public void onAdded(Event event) {\n"
                        "        Runnable r = () -> event.touch();\n"
                        "        r.run();\n"
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
                "    public void onAdded(Event event) {\n"
                "        Runnable r = () -> event2.touch();\n"
                "        r.run();\n"
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
                    str(root / "before-indy-capture-alias"),
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
                "Runnable r = () -> event.touch();",
                normalized,
            )
            self.assertNotIn("event2", normalized)

            action = next(
                row
                for row in report["actions"]
                if row["kind"]
                == "invokedynamic_parameter_capture_alias"
            )
            self.assertEqual(action["method_name"], "onAdded")
            self.assertEqual(
                action["method_descriptor"],
                "(Lp/Event;)V",
            )
            self.assertEqual(action["parameter_name"], "event")
            self.assertEqual(action["alias_name"], "event2")
            self.assertEqual(action["replacement_count"], 1)
            self.assertEqual(
                len(action["invokedynamic_callsites"]),
                1,
            )
            self.assertEqual(
                report["summary"][
                    "invokedynamic_parameter_capture_alias_reference_count"
                ],
                1,
            )

            after = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "after-indy-capture-alias"),
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

    def test_invokedynamic_parameter_capture_alias_supports_bare_arguments(
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
                        "    private static void use(String value) {}\n"
                        "    public static void open(String url) {\n"
                        "        Runnable r = () -> use(url);\n"
                        "        r.run();\n"
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
                "    private static void use(String value) {}\n"
                "    public static void open(String url) {\n"
                "        Runnable r = () -> use(url2);\n"
                "        r.run();\n"
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
                    str(root / "before-bare-indy-alias"),
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
            self.assertIn("Runnable r = () -> use(url);", normalized)
            self.assertNotIn("url2", normalized)

            action = next(
                row
                for row in report["actions"]
                if row["kind"]
                == "invokedynamic_parameter_capture_alias"
            )
            self.assertEqual(action["parameter_name"], "url")
            self.assertEqual(action["alias_name"], "url2")
            self.assertEqual(action["replacement_count"], 1)

            after = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "after-bare-indy-alias"),
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

    def test_bare_invokedynamic_alias_is_not_rewritten_when_declared(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "p/Client.java": (
                        "package p;\n"
                        "public class Client {\n"
                        "    private static void use(String value) {}\n"
                        "    public static void open(String url) {\n"
                        "        Runnable r = () -> use(url);\n"
                        "        r.run();\n"
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
                "    private static void use(String value) {}\n"
                "    public static void open(String url) {\n"
                "        String url2 = url;\n"
                "        Runnable r = () -> use(url2);\n"
                "        r.run();\n"
                "    }\n"
                "}\n"
            )
            source.write_text(original, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)

            self.assertEqual(source.read_text(encoding="utf-8"), original)
            self.assertEqual(
                report["summary"][
                    "invokedynamic_parameter_capture_alias_reference_count"
                ],
                0,
            )

    def test_invokedynamic_lambda_outer_capture_collision_uses_bootstrap_helper(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "p/A.java": (
                        "package p;\n"
                        "import java.util.Arrays;\n"
                        "public class A {\n"
                        "    public static long count(String prefix) {\n"
                        "        return Arrays.asList(\"a\", \"ab\").stream()\n"
                        "            .filter(value -> value.startsWith(prefix))\n"
                        "            .count();\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package p;\n"
                "import java.util.Arrays;\n"
                "public class A {\n"
                "    public static long count(String prefix) {\n"
                "        return Arrays.asList(\"a\", \"ab\").stream()\n"
                "            .filter(prefix -> prefix.startsWith(captured))\n"
                "            .count();\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )

            before = subprocess.run(
                [
                    "javac",
                    "-d",
                    str(root / "before-lambda-capture-collision"),
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(before.returncode, 0)

            report = normalize_procyon_source(root / "src", jar)
            normalized = source.read_text(encoding="utf-8")
            self.assertNotIn("startsWith(captured)", normalized)
            self.assertNotIn(".filter(prefix ->", normalized)
            self.assertIn("startsWith(prefix)", normalized)
            self.assertRegex(
                normalized,
                r"\.filter\(recoveredLambdaArg_[0-9a-f]{12}"
                r" -> recoveredLambdaArg_[0-9a-f]{12}"
                r"\.startsWith\(prefix\)\)",
            )

            action = next(
                row
                for row in report["actions"]
                if row["kind"]
                == "invokedynamic_lambda_outer_capture_collision"
            )
            self.assertEqual(
                action["outer_parameter_name"],
                "prefix",
            )
            self.assertEqual(
                action["outer_parameter_slot"],
                0,
            )
            self.assertEqual(
                action["undeclared_capture_alias"],
                "captured",
            )
            self.assertEqual(
                action["member_name"],
                "startsWith",
            )
            self.assertEqual(
                action["invokedynamic"]["helper_descriptor"],
                "(Ljava/lang/String;Ljava/lang/String;)Z",
            )
            self.assertEqual(action["replacement_count"], 3)
            self.assertEqual(
                report["summary"][
                    "invokedynamic_lambda_outer_capture_collision_action_count"
                ],
                1,
            )

            after = subprocess.run(
                [
                    "javac",
                    "-d",
                    str(root / "after-lambda-capture-collision"),
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

    def test_invokedynamic_lambda_outer_capture_collision_rejects_bootstrap_descriptor_drift(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "p/A.java": (
                        "package p;\n"
                        "import java.util.Arrays;\n"
                        "public class A {\n"
                        "    public static long count(String prefix) {\n"
                        "        return Arrays.asList(\"a\", \"ab\").stream()\n"
                        "            .filter(value -> value.startsWith(prefix))\n"
                        "            .count();\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            malformed = (
                "package p;\n"
                "import java.util.Arrays;\n"
                "public class A {\n"
                "    public static long count(String prefix) {\n"
                "        return Arrays.asList(\"a\", \"ab\").stream()\n"
                "            .filter(prefix -> prefix.startsWith(captured))\n"
                "            .count();\n"
                "    }\n"
                "}\n"
            )
            source.write_text(malformed, encoding="utf-8")

            def drifted_profile(data: bytes):
                profile = profile_class_field_accesses_exact(data)
                changed = 0
                for bootstrap in profile.get("bootstrap_methods", []):
                    handle = bootstrap.get("bootstrap_method", {})
                    if (
                        handle.get("owner")
                        == "java/lang/invoke/LambdaMetafactory"
                    ):
                        handle["descriptor"] = "()V"
                        changed += 1
                self.assertEqual(changed, 1)
                return profile

            with mock.patch(
                "spk_recovery.source_normalization."
                "profile_class_field_accesses",
                side_effect=drifted_profile,
            ):
                report = normalize_procyon_source(root / "src", jar)

            self.assertEqual(
                source.read_text(encoding="utf-8"),
                malformed,
            )
            self.assertEqual(
                report["summary"][
                    "invokedynamic_lambda_outer_capture_collision_action_count"
                ],
                0,
            )

    def test_invokedynamic_lambda_outer_capture_collision_requires_exact_outer_slot(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "p/A.java": (
                        "package p;\n"
                        "import java.util.Arrays;\n"
                        "public class A {\n"
                        "    public static long count(String wrong, String prefix) {\n"
                        "        return Arrays.asList(\"a\", \"ab\").stream()\n"
                        "            .filter(value -> value.startsWith(prefix))\n"
                        "            .count();\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            malformed = (
                "package p;\n"
                "import java.util.Arrays;\n"
                "public class A {\n"
                "    public static long count(String wrong, String prefix) {\n"
                "        return Arrays.asList(\"a\", \"ab\").stream()\n"
                "            .filter(wrong -> wrong.startsWith(captured))\n"
                "            .count();\n"
                "    }\n"
                "}\n"
            )
            source.write_text(malformed, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)

            self.assertEqual(
                source.read_text(encoding="utf-8"),
                malformed,
            )
            self.assertEqual(
                report["summary"][
                    "invokedynamic_lambda_outer_capture_collision_action_count"
                ],
                0,
            )

    def test_invokedynamic_lambda_outer_capture_collision_fails_on_helper_member_drift(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "p/A.java": (
                        "package p;\n"
                        "import java.util.Arrays;\n"
                        "public class A {\n"
                        "    public static long count(String prefix) {\n"
                        "        return Arrays.asList(\"a\", \"ab\").stream()\n"
                        "            .filter(value -> value.endsWith(prefix))\n"
                        "            .count();\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            malformed = (
                "package p;\n"
                "import java.util.Arrays;\n"
                "public class A {\n"
                "    public static long count(String prefix) {\n"
                "        return Arrays.asList(\"a\", \"ab\").stream()\n"
                "            .filter(prefix -> prefix.startsWith(captured))\n"
                "            .count();\n"
                "    }\n"
                "}\n"
            )
            source.write_text(malformed, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)

            self.assertEqual(
                source.read_text(encoding="utf-8"),
                malformed,
            )
            self.assertEqual(
                report["summary"][
                    "invokedynamic_lambda_outer_capture_collision_action_count"
                ],
                0,
            )

    def test_invokedynamic_parameter_alias_requires_capture_proof(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "p/Event.java": (
                        "package p;\n"
                        "public interface Event { void touch(); }\n"
                    ),
                    "p/Client.java": (
                        "package p;\n"
                        "public class Client {\n"
                        "    public void onAdded(Event event) {\n"
                        "        System.out.println(\"no lambda\");\n"
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
                "    public void onAdded(Event event) {\n"
                "        event2.touch();\n"
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
                    "invokedynamic_parameter_capture_alias_reference_count"
                ],
                0,
            )


    def test_erased_generic_constructor_argument_cast_uses_exact_call(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "p/Cache.java": (
                        "package p;\n"
                        "public class Cache<K, V> {\n"
                        "    public V e(K key) { return null; }\n"
                        "}\n"
                    ),
                    "p/Key.java": (
                        "package p;\n"
                        "public class Key {\n"
                        "    public Key(int value) {}\n"
                        "}\n"
                    ),
                    "p/Buffer.java": (
                        "package p;\n"
                        "public class Buffer {}\n"
                    ),
                    "p/A.java": (
                        "package p;\n"
                        "public class A {\n"
                        "    private final Cache<Key, Buffer> cache = new Cache<>();\n"
                        "    public Buffer get(int value) {\n"
                        "        return cache.e(new Key(value));\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package p;\n"
                "public class A {\n"
                "    private final Cache<Key, Buffer> cache = new Cache<>();\n"
                "    public Buffer get(int value) {\n"
                "        return (Buffer)this.cache.e((Object)new Key(value));\n"
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
                    str(root / "before-erased-generic-cast"),
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(before.returncode, 0)

            report = normalize_procyon_source(root / "src", jar)
            normalized = source.read_text(encoding="utf-8")
            self.assertIn(
                "this.cache.e(new Key(value))",
                normalized,
            )
            self.assertNotIn("(Object)new Key", normalized)

            action = next(
                row
                for row in report["actions"]
                if row["kind"]
                == "erased_generic_constructor_argument_cast_removal"
            )
            self.assertEqual(action["field_name"], "cache")
            self.assertEqual(action["key_source_type"], "Key")
            self.assertEqual(action["value_source_type"], "Buffer")
            self.assertEqual(action["replacement_count"], 1)
            self.assertEqual(
                report["summary"][
                    "erased_generic_constructor_argument_cast_action_count"
                ],
                1,
            )

            after = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "after-erased-generic-cast"),
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

    def test_erased_generic_constructor_argument_cast_requires_field_owner(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "p/Cache.java": (
                        "package p;\n"
                        "public class Cache<K, V> {\n"
                        "    public V e(K key) { return null; }\n"
                        "}\n"
                    ),
                    "p/Key.java": (
                        "package p;\n"
                        "public class Key { public Key(int value) {} }\n"
                    ),
                    "p/Buffer.java": (
                        "package p;\n"
                        "public class Buffer {}\n"
                    ),
                    "p/A.java": (
                        "package p;\n"
                        "public class A {\n"
                        "    private final Cache<Key, Buffer> cache = new Cache<>();\n"
                        "    public Buffer get(int value) {\n"
                        "        return cache.e(new Key(value));\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            original = (
                "package p;\n"
                "public class A {\n"
                "    private final OtherCache<Key, Buffer> cache = null;\n"
                "    public Buffer get(int value) {\n"
                "        return (Buffer)this.cache.e((Object)new Key(value));\n"
                "    }\n"
                "}\n"
            )
            source.write_text(original, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)

            self.assertEqual(source.read_text(encoding="utf-8"), original)
            self.assertEqual(
                report["summary"][
                    "erased_generic_constructor_argument_cast_action_count"
                ],
                0,
            )

    def test_erased_generic_constructor_argument_cast_fails_on_return_drift(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "p/Cache.java": (
                        "package p;\n"
                        "public class Cache<K, V> {\n"
                        "    public V e(K key) { return null; }\n"
                        "}\n"
                    ),
                    "p/Key.java": (
                        "package p;\n"
                        "public class Key { public Key(int value) {} }\n"
                    ),
                    "p/Buffer.java": (
                        "package p;\n"
                        "public class Buffer {}\n"
                    ),
                    "p/A.java": (
                        "package p;\n"
                        "public class A {\n"
                        "    private final Cache<Key, Buffer> cache = new Cache<>();\n"
                        "    public Object get(int value) {\n"
                        "        return cache.e(new Key(value));\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            original = (
                "package p;\n"
                "public class A {\n"
                "    private final Cache<Key, Buffer> cache = new Cache<>();\n"
                "    public Buffer get(int value) {\n"
                "        return (Buffer)this.cache.e((Object)new Key(value));\n"
                "    }\n"
                "}\n"
            )
            source.write_text(original, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)

            self.assertEqual(source.read_text(encoding="utf-8"), original)
            self.assertEqual(
                report["summary"][
                    "erased_generic_constructor_argument_cast_action_count"
                ],
                0,
            )

    def test_invokedynamic_image_loader_locals_use_exact_slot_flows(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "p/Task.java": (
                        "package p;\n"
                        "@FunctionalInterface\n"
                        "public interface Task { boolean loop(); }\n"
                    ),
                    "p/Registry.java": (
                        "package p;\n"
                        "public class Registry {\n"
                        "    public static void add(String key, Task task) {}\n"
                        "}\n"
                    ),
                    "p/Client.java": (
                        "package p;\n"
                        "public class Client { public boolean enabled = true; }\n"
                    ),
                    "p/Gate.java": (
                        "package p;\n"
                        "public class Gate {\n"
                        "    public static Gate launcher() { return new Gate(); }\n"
                        "    public Client client() { return new Client(); }\n"
                        "}\n"
                    ),
                    "p/Buffer.java": (
                        "package p;\n"
                        "import java.awt.image.BufferedImage;\n"
                        "public class Buffer extends BufferedImage {\n"
                        "    public Buffer(int width, int height, int type) {\n"
                        "        super(width, height, BufferedImage.TYPE_INT_ARGB);\n"
                        "    }\n"
                        "    public void ready() {}\n"
                        "}\n"
                    ),
                    "p/Sprite.java": (
                        "package p;\n"
                        "import java.awt.Color;\n"
                        "import java.awt.Image;\n"
                        "import java.awt.image.BufferedImage;\n"
                        "public class Sprite {\n"
                        "    public int width = 16;\n"
                        "    public int height = 16;\n"
                        "    public Sprite(String path) {}\n"
                        "    public void init(String path) {}\n"
                        "    public static Sprite load(int a, int b, int c, int d) {\n"
                        "        return new Sprite(\"\");\n"
                        "    }\n"
                        "    public static Image load(String path) {\n"
                        "        return new BufferedImage(1, 1, BufferedImage.TYPE_INT_ARGB);\n"
                        "    }\n"
                        "    public Image image(int width, int height) {\n"
                        "        return new BufferedImage(1, 1, BufferedImage.TYPE_INT_ARGB);\n"
                        "    }\n"
                        "    public static Image tint(Image image, Color color) {\n"
                        "        return image;\n"
                        "    }\n"
                        "}\n"
                    ),
                    "p/A.java": (
                        "package p;\n"
                        "import java.awt.Color;\n"
                        "import java.awt.Graphics2D;\n"
                        "import java.awt.Image;\n"
                        "public class A {\n"
                        "    private Buffer b(int n, int n2, int n3) {\n"
                        "        final Buffer d = new Buffer(36, 32, 2);\n"
                        "        Registry.add(\"Ico_\" + n + \"_\" + n3, () -> {\n"
                        "            if (!Gate.launcher().client().enabled) {\n"
                        "                return true;\n"
                        "            }\n"
                        "            Sprite f = Sprite.load(n, n2, 0, n3);\n"
                        "            if (f == null) return true;\n"
                        "            Image image = f.image(32, 32);\n"
                        "            image = Sprite.tint(image, new Color(0, 0, 0));\n"
                        "            Graphics2D graphics2D = d.createGraphics();\n"
                        "            graphics2D.drawImage(image, 0, 0, null);\n"
                        "            graphics2D.dispose();\n"
                        "            d.ready();\n"
                        "            return false;\n"
                        "        });\n"
                        "        return d;\n"
                        "    }\n"
                        "    private Buffer b(String s, int n) {\n"
                        "        int n2 = n;\n"
                        "        int o = n;\n"
                        "        if (n == -1) {\n"
                        "            Sprite f = new Sprite(s);\n"
                        "            f.init(s);\n"
                        "            n2 = f.width;\n"
                        "            o = f.height;\n"
                        "        }\n"
                        "        Image image = Sprite.load(s);\n"
                        "        final Buffer d = new Buffer(n2, o, 2);\n"
                        "        Registry.add(\"Ico_\" + s + \"_\" + n, () -> {\n"
                        "            try {\n"
                        "                if (image == null || image.getWidth(null) <= 0 || image.getHeight(null) <= 0) return true;\n"
                        "                Graphics2D graphics2D = d.createGraphics();\n"
                        "                graphics2D.drawImage(image, 0, 0, null);\n"
                        "                graphics2D.dispose();\n"
                        "                d.ready();\n"
                        "                return false;\n"
                        "            } catch (Exception ex) {\n"
                        "                ex.printStackTrace();\n"
                        "                return true;\n"
                        "            }\n"
                        "        });\n"
                        "        return d;\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package p;\n"
                "import java.awt.Color;\n"
                "import java.awt.Graphics2D;\n"
                "import java.awt.Image;\n"
                "public class A {\n"
                "    private Buffer b(int n, int n2, int n3) {\n"
                "        final Buffer d = new Buffer(36, 32, 2);\n"
                "        Registry.add(\"Ico_\" + n + \"_\" + n3, () -> {\n"
                "            if (!Gate.launcher().client().enabled) {\n"
                "                return true;\n"
                "            }\n"
                "            else {\n"
                "                Sprite.load(n4, n5, 0, n6);\n"
                "                final Sprite f;\n"
                "                if (f == null) return true;\n"
                "                Sprite.tint(f.image(32, 32), new Color(0, 0, 0));\n"
                "                d2.createGraphics();\n"
                "                final Graphics2D graphics2D;\n"
                "                final Image image;\n"
                "                graphics2D.drawImage(image, 0, 0, null);\n"
                "                graphics2D.dispose();\n"
                "                d2.ready();\n"
                "                return false;\n"
                "            }\n"
                "        });\n"
                "        return d;\n"
                "    }\n"
                "    private Buffer b(String s, int n) {\n"
                "        int n2 = n;\n"
                "        int o = n;\n"
                "        if (n == -1) {\n"
                "            final Sprite f = new Sprite(s);\n"
                "            f.init(s);\n"
                "            n2 = f.width;\n"
                "            o = f.height;\n"
                "        }\n"
                "        Sprite.load(s);\n"
                "        final Buffer d = new Buffer(n2, o, 2);\n"
                "        Registry.add(\"Ico_\" + s + \"_\" + n, () -> {\n"
                "            try {\n"
                "                if (image == null || image.getWidth(null) <= 0 || image.getHeight(null) <= 0) return true;\n"
                "                d2.createGraphics();\n"
                "                final Graphics2D graphics2D;\n"
                "                final Image image;\n"
                "                graphics2D.drawImage(image, 0, 0, null);\n"
                "                graphics2D.dispose();\n"
                "                d2.ready();\n"
                "                return false;\n"
                "            } catch (Exception ex) {\n"
                "                ex.printStackTrace();\n"
                "                return true;\n"
                "            }\n"
                "        });\n"
                "        return d;\n"
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
                    str(root / "before-image-loader"),
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(before.returncode, 0)

            report = normalize_procyon_source(root / "src", jar)
            normalized = source.read_text(encoding="utf-8")

            self.assertIn(
                "final Sprite f = Sprite.load(n, n2, 0, n3);",
                normalized,
            )
            self.assertIn(
                "final Image image = Sprite.tint("
                "f.image(32, 32), new Color(0, 0, 0));",
                normalized,
            )
            self.assertIn(
                "final Image image = Sprite.load(s);",
                normalized,
            )
            self.assertIn(
                "final Graphics2D graphics2D = d.createGraphics();",
                normalized,
            )
            self.assertNotIn("n4", normalized)
            self.assertNotIn("n5", normalized)
            self.assertNotIn("n6", normalized)
            self.assertNotIn("d2.", normalized)
            self.assertNotIn("final Image image;", normalized)

            actions = [
                row
                for row in report["actions"]
                if row["kind"]
                == "invokedynamic_image_loader_local_reconstruction"
            ]
            self.assertEqual(
                [row["variant"] for row in actions],
                ["three_int", "string_int"],
            )
            self.assertEqual(
                report["summary"][
                    "invokedynamic_image_loader_local_action_count"
                ],
                2,
            )
            self.assertEqual(
                report["summary"][
                    "invokedynamic_image_loader_local_reference_count"
                ],
                9,
            )

            after = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "after-image-loader"),
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

    def test_invokedynamic_image_loader_locals_fail_closed_on_buffer_drift(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "p/Task.java": (
                        "package p;\n"
                        "@FunctionalInterface public interface Task { boolean loop(); }\n"
                    ),
                    "p/Registry.java": (
                        "package p;\n"
                        "public class Registry { public static void add(String key, Task task) {} }\n"
                    ),
                    "p/Client.java": (
                        "package p;\n"
                        "public class Client { public boolean enabled = true; }\n"
                    ),
                    "p/Gate.java": (
                        "package p;\n"
                        "public class Gate {\n"
                        " public static Gate launcher() { return new Gate(); }\n"
                        " public Client client() { return new Client(); }\n"
                        "}\n"
                    ),
                    "p/Buffer.java": (
                        "package p;\n"
                        "import java.awt.image.BufferedImage;\n"
                        "public class Buffer extends BufferedImage {\n"
                        " public Buffer(int a,int b,int c){super(a,b,BufferedImage.TYPE_INT_ARGB);}\n"
                        " public void ready() {}\n"
                        "}\n"
                    ),
                    "p/Sprite.java": (
                        "package p;\n"
                        "import java.awt.Color; import java.awt.Image;\n"
                        "import java.awt.image.BufferedImage;\n"
                        "public class Sprite {\n"
                        " public static Sprite load(int a,int b,int c,int d){return new Sprite();}\n"
                        " public Image image(int a,int b){return new BufferedImage(1,1,2);}\n"
                        " public static Image tint(Image i,Color c){return i;}\n"
                        "}\n"
                    ),
                    "p/A.java": (
                        "package p;\n"
                        "import java.awt.Color; import java.awt.Graphics2D; import java.awt.Image;\n"
                        "public class A {\n"
                        " private Buffer b(int n,int n2,int n3){\n"
                        "  final Buffer d=new Buffer(35,32,2);\n"
                        "  Registry.add(\"Ico_\"+n+\"_\"+n3,()->{\n"
                        "   if(!Gate.launcher().client().enabled)return true;\n"
                        "   Sprite f=Sprite.load(n,n2,0,n3); if(f==null)return true;\n"
                        "   Image image=Sprite.tint(f.image(32,32),new Color(0,0,0));\n"
                        "   Graphics2D g=d.createGraphics(); g.drawImage(image,0,0,null); g.dispose(); d.ready(); return false;\n"
                        "  }); return d;\n"
                        " }\n"
                        "}\n"
                    ),
                },
            )
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            original = (
                "package p;\n"
                "import java.awt.Color; import java.awt.Graphics2D; import java.awt.Image;\n"
                "public class A {\n"
                " private Buffer b(int n,int n2,int n3){\n"
                "  final Buffer d=new Buffer(36,32,2);\n"
                "  Registry.add(\"Ico_\"+n+\"_\"+n3,()->{\n"
                "   Sprite.load(n4,n5,0,n6);\n"
                "   final Sprite f;\n"
                "   if(f==null)return true;\n"
                "   Sprite.tint(f.image(32,32),new Color(0,0,0));\n"
                "   d2.createGraphics();\n"
                "   final Graphics2D g;\n"
                "   final Image image;\n"
                "   g.drawImage(image,0,0,null); g.dispose(); d2.ready(); return false;\n"
                "  }); return d;\n"
                " }\n"
                "}\n"
            )
            source.write_text(original, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)

            self.assertEqual(source.read_text(encoding="utf-8"), original)
            self.assertEqual(
                report["summary"][
                    "invokedynamic_image_loader_local_action_count"
                ],
                0,
            )

    def test_dimension_capture_locals_use_exact_slot_flow(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "p/A.java": (
                        "package p;\n"
                        "import java.awt.Dimension;\n"
                        "import javax.swing.JPanel;\n"
                        "import javax.swing.SwingUtilities;\n"
                        "public class A {\n"
                        "    private final JPanel panel = new JPanel();\n"
                        "    public void resize(int width, int height, int minWidth, int minHeight) {\n"
                        "        int boundedWidth = Math.max(Math.min(width, 7680), minWidth);\n"
                        "        int boundedHeight = Math.max(Math.min(height, 2160), minHeight);\n"
                        "        Dimension preferred = new Dimension(boundedWidth, boundedHeight);\n"
                        "        Dimension minimum = new Dimension(minWidth, minHeight);\n"
                        "        SwingUtilities.invokeLater(() -> {\n"
                        "            panel.setSize(preferred);\n"
                        "            panel.setPreferredSize(preferred);\n"
                        "            panel.setMinimumSize(minimum);\n"
                        "        });\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package p;\n"
                "import java.awt.Dimension;\n"
                "import javax.swing.JPanel;\n"
                "import javax.swing.SwingUtilities;\n"
                "public class A {\n"
                "    private final JPanel panel = new JPanel();\n"
                "    public void resize(int width, int height, int minWidth, int minHeight) {\n"
                "        final Object o = new Dimension(Math.max(Math.min(missingWidth, 7680), n5), Math.max(Math.min(missingHeight, 2160), n6));\n"
                "        final Object o2 = new Dimension(n5, n6);\n"
                "        SwingUtilities.invokeLater(() -> {\n"
                "            panel.setSize(dimension);\n"
                "            panel.setPreferredSize(dimension);\n"
                "            panel.setMinimumSize(dimension2);\n"
                "        });\n"
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
                    str(root / "before-dimension-capture"),
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
                "final Dimension dimension = new Dimension("
                "Math.max(Math.min(width, 7680), minWidth), "
                "Math.max(Math.min(height, 2160), minHeight));",
                normalized,
            )
            self.assertIn(
                "final Dimension dimension2 = "
                "new Dimension(minWidth, minHeight);",
                normalized,
            )
            self.assertNotIn("final Object o =", normalized)
            self.assertNotIn("final Object o2 =", normalized)

            action = next(
                row
                for row in report["actions"]
                if row["kind"]
                == "dimension_capture_local_reconstruction"
            )
            self.assertEqual(action["method_name"], "resize")
            self.assertEqual(action["method_descriptor"], "(IIII)V")
            self.assertEqual(
                action["parameter_names"],
                ["width", "height", "minWidth", "minHeight"],
            )
            self.assertEqual(
                action["slot_evidence"],
                {
                    "first_int_slot": 5,
                    "second_int_slot": 6,
                    "first_dimension_slot": 7,
                    "second_dimension_slot": 8,
                },
            )
            self.assertEqual(action["replacement_count"], 2)
            self.assertEqual(
                report["summary"][
                    "dimension_capture_local_action_count"
                ],
                1,
            )
            self.assertEqual(
                report["summary"][
                    "dimension_capture_local_declaration_replacement_count"
                ],
                2,
            )

            after = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "after-dimension-capture"),
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

    def test_dimension_capture_locals_fail_closed_on_constant_drift(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "p/A.java": (
                        "package p;\n"
                        "import java.awt.Dimension;\n"
                        "import javax.swing.JPanel;\n"
                        "import javax.swing.SwingUtilities;\n"
                        "public class A {\n"
                        "    private final JPanel panel = new JPanel();\n"
                        "    public void resize(int width, int height, int minWidth, int minHeight) {\n"
                        "        int boundedWidth = Math.max(Math.min(width, 7679), minWidth);\n"
                        "        int boundedHeight = Math.max(Math.min(height, 2160), minHeight);\n"
                        "        Dimension preferred = new Dimension(boundedWidth, boundedHeight);\n"
                        "        Dimension minimum = new Dimension(minWidth, minHeight);\n"
                        "        SwingUtilities.invokeLater(() -> {\n"
                        "            panel.setSize(preferred);\n"
                        "            panel.setPreferredSize(preferred);\n"
                        "            panel.setMinimumSize(minimum);\n"
                        "        });\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            original = (
                "package p;\n"
                "import java.awt.Dimension;\n"
                "import javax.swing.JPanel;\n"
                "import javax.swing.SwingUtilities;\n"
                "public class A {\n"
                "    private final JPanel panel = new JPanel();\n"
                "    public void resize(int width, int height, int minWidth, int minHeight) {\n"
                "        final Object o = new Dimension(Math.max(Math.min(missingWidth, 7680), n5), Math.max(Math.min(missingHeight, 2160), n6));\n"
                "        final Object o2 = new Dimension(n5, n6);\n"
                "        SwingUtilities.invokeLater(() -> {\n"
                "            panel.setSize(dimension);\n"
                "            panel.setPreferredSize(dimension);\n"
                "            panel.setMinimumSize(dimension2);\n"
                "        });\n"
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
                    "dimension_capture_local_action_count"
                ],
                0,
            )

    def test_exact_parameter_receiver_alias_uses_slot1_receiver(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "rs/runelite/events/ClientShutdown.java": (
                        "package rs.runelite.events;\n"
                        "import java.time.Duration;\n"
                        "public class ClientShutdown {\n"
                        "    public void waitForAllConsumers(Duration duration) {}\n"
                        "}\n"
                    ),
                    "p/A.java": (
                        "package p;\n"
                        "import java.time.Duration;\n"
                        "import rs.runelite.events.ClientShutdown;\n"
                        "public class A {\n"
                        "    private void shutdown(ClientShutdown event) {\n"
                        "        event.waitForAllConsumers(Duration.ofSeconds(10L));\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )
            source_root = root / "src"
            event_source = (
                source_root
                / "rs"
                / "runelite"
                / "events"
                / "ClientShutdown.java"
            )
            source = source_root / "p" / "A.java"
            event_source.parent.mkdir(parents=True)
            source.parent.mkdir(parents=True)
            event_source.write_text(
                "package rs.runelite.events;\n"
                "import java.time.Duration;\n"
                "public class ClientShutdown {\n"
                "    public void waitForAllConsumers(Duration duration) {}\n"
                "}\n",
                encoding="utf-8",
            )
            source.write_text(
                "package p;\n"
                "import java.time.Duration;\n"
                "import rs.runelite.events.ClientShutdown;\n"
                "public class A {\n"
                "    private void shutdown(ClientShutdown event) {\n"
                "        clientShutdown.waitForAllConsumers(Duration.ofSeconds(10L));\n"
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
                    str(root / "before-parameter-receiver"),
                    str(event_source),
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(before.returncode, 0)
            self.assertIn("cannot find symbol", before.stderr)

            report = normalize_procyon_source(source_root, jar)
            normalized = source.read_text(encoding="utf-8")
            self.assertIn(
                "event.waitForAllConsumers(Duration.ofSeconds(10L));",
                normalized,
            )
            self.assertNotIn("clientShutdown.", normalized)

            action = next(
                row
                for row in report["actions"]
                if row["kind"] == "exact_parameter_receiver_alias"
            )
            self.assertEqual(action["method_name"], "shutdown")
            self.assertEqual(
                action["method_descriptor"],
                "(Lrs/runelite/events/ClientShutdown;)V",
            )
            self.assertEqual(action["parameter_name"], "event")
            self.assertEqual(action["alias_name"], "clientShutdown")
            self.assertEqual(action["replacement_count"], 1)
            self.assertEqual(
                report["summary"][
                    "exact_parameter_receiver_alias_reference_count"
                ],
                1,
            )

            after = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "after-parameter-receiver"),
                    str(event_source),
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

    def test_exact_parameter_receiver_alias_requires_slot1_flow(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "rs/runelite/events/ClientShutdown.java": (
                        "package rs.runelite.events;\n"
                        "import java.time.Duration;\n"
                        "public class ClientShutdown {\n"
                        "    public void waitForAllConsumers(Duration duration) {}\n"
                        "}\n"
                    ),
                    "p/A.java": (
                        "package p;\n"
                        "import java.time.Duration;\n"
                        "import rs.runelite.events.ClientShutdown;\n"
                        "public class A {\n"
                        "    private void shutdown(ClientShutdown event) {\n"
                        "        new ClientShutdown().waitForAllConsumers(Duration.ofSeconds(10L));\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )
            source_root = root / "src"
            event_source = (
                source_root
                / "rs"
                / "runelite"
                / "events"
                / "ClientShutdown.java"
            )
            source = source_root / "p" / "A.java"
            event_source.parent.mkdir(parents=True)
            source.parent.mkdir(parents=True)
            event_source.write_text(
                "package rs.runelite.events;\n"
                "import java.time.Duration;\n"
                "public class ClientShutdown {\n"
                "    public void waitForAllConsumers(Duration duration) {}\n"
                "}\n",
                encoding="utf-8",
            )
            original = (
                "package p;\n"
                "import java.time.Duration;\n"
                "import rs.runelite.events.ClientShutdown;\n"
                "public class A {\n"
                "    private void shutdown(ClientShutdown event) {\n"
                "        clientShutdown.waitForAllConsumers(Duration.ofSeconds(10L));\n"
                "    }\n"
                "}\n"
            )
            source.write_text(original, encoding="utf-8")

            report = normalize_procyon_source(source_root, jar)

            self.assertEqual(
                source.read_text(encoding="utf-8"),
                original,
            )
            self.assertEqual(
                report["summary"][
                    "exact_parameter_receiver_alias_reference_count"
                ],
                0,
            )

    def test_hidden_layout_constructor_arguments_use_exact_descriptor(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "p/Client.java": (
                        "package p;\n"
                        "import java.awt.LayoutManager;\n"
                        "import javax.swing.JComponent;\n"
                        "public class Client {\n"
                        "    public void wrap(JComponent component) {\n"
                        "        LayoutManager saved = component.getLayout();\n"
                        "        component.setLayout(new Wrapper(this, saved, component));\n"
                        "    }\n"
                        "}\n"
                    ),
                    "p/Wrapper.java": (
                        "package p;\n"
                        "import java.awt.Component;\n"
                        "import java.awt.Container;\n"
                        "import java.awt.Dimension;\n"
                        "import java.awt.LayoutManager;\n"
                        "import javax.swing.JComponent;\n"
                        "public class Wrapper implements LayoutManager {\n"
                        "    Wrapper(Client owner, LayoutManager saved, JComponent component) {}\n"
                        "    public void addLayoutComponent(String name, Component comp) {}\n"
                        "    public void removeLayoutComponent(Component comp) {}\n"
                        "    public Dimension preferredLayoutSize(Container parent) { return new Dimension(); }\n"
                        "    public Dimension minimumLayoutSize(Container parent) { return new Dimension(); }\n"
                        "    public void layoutContainer(Container parent) {}\n"
                        "}\n"
                    ),
                },
            )
            source_root = root / "src"
            client = source_root / "p" / "Client.java"
            wrapper = source_root / "p" / "Wrapper.java"
            client.parent.mkdir(parents=True)
            client.write_text(
                "package p;\n"
                "import java.awt.LayoutManager;\n"
                "import javax.swing.JComponent;\n"
                "public class Client {\n"
                "    public void wrap(JComponent component) {\n"
                "        final LayoutManager saved = component.getLayout();\n"
                "        component.setLayout(new Wrapper());\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )
            wrapper.write_text(
                "package p;\n"
                "import java.awt.Component;\n"
                "import java.awt.Container;\n"
                "import java.awt.Dimension;\n"
                "import java.awt.LayoutManager;\n"
                "import javax.swing.JComponent;\n"
                "public class Wrapper implements LayoutManager {\n"
                "    Wrapper(Client owner, LayoutManager saved, JComponent component) {}\n"
                "    public void addLayoutComponent(String name, Component comp) {}\n"
                "    public void removeLayoutComponent(Component comp) {}\n"
                "    public Dimension preferredLayoutSize(Container parent) { return new Dimension(); }\n"
                "    public Dimension minimumLayoutSize(Container parent) { return new Dimension(); }\n"
                "    public void layoutContainer(Container parent) {}\n"
                "}\n",
                encoding="utf-8",
            )

            before = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "before-hidden-layout-ctor"),
                    str(client),
                    str(wrapper),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(before.returncode, 0)
            self.assertIn(
                "constructor Wrapper",
                before.stderr,
            )

            report = normalize_procyon_source(source_root, jar)
            normalized = client.read_text(encoding="utf-8")
            self.assertIn(
                "component.setLayout(new Wrapper(this, saved, component));",
                normalized,
            )
            action = next(
                row
                for row in report["actions"]
                if row["kind"]
                == "hidden_layout_constructor_arguments"
            )
            self.assertEqual(action["method_name"], "wrap")
            self.assertEqual(
                action["method_descriptor"],
                "(Ljavax/swing/JComponent;)V",
            )
            self.assertEqual(action["target_owner"], "p/Wrapper")
            self.assertEqual(
                action["constructor_descriptor"],
                "(Lp/Client;Ljava/awt/LayoutManager;Ljavax/swing/JComponent;)V",
            )
            self.assertEqual(action["component_name"], "component")
            self.assertEqual(action["layout_name"], "saved")
            self.assertEqual(action["replacement_count"], 1)
            self.assertEqual(
                report["summary"][
                    "hidden_layout_constructor_argument_reference_count"
                ],
                1,
            )

            after = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "after-hidden-layout-ctor"),
                    str(client),
                    str(wrapper),
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

    def test_hidden_layout_constructor_arguments_fail_without_exact_shape(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "p/Client.java": (
                        "package p;\n"
                        "import java.awt.LayoutManager;\n"
                        "import javax.swing.JComponent;\n"
                        "public class Client {\n"
                        "    public void wrap(JComponent component) {\n"
                        "        LayoutManager saved = component.getLayout();\n"
                        "        component.setLayout(new Wrapper(saved, component));\n"
                        "    }\n"
                        "}\n"
                    ),
                    "p/Wrapper.java": (
                        "package p;\n"
                        "import java.awt.Component;\n"
                        "import java.awt.Container;\n"
                        "import java.awt.Dimension;\n"
                        "import java.awt.LayoutManager;\n"
                        "import javax.swing.JComponent;\n"
                        "public class Wrapper implements LayoutManager {\n"
                        "    Wrapper(LayoutManager saved, JComponent component) {}\n"
                        "    public void addLayoutComponent(String name, Component comp) {}\n"
                        "    public void removeLayoutComponent(Component comp) {}\n"
                        "    public Dimension preferredLayoutSize(Container parent) { return new Dimension(); }\n"
                        "    public Dimension minimumLayoutSize(Container parent) { return new Dimension(); }\n"
                        "    public void layoutContainer(Container parent) {}\n"
                        "}\n"
                    ),
                },
            )
            source_root = root / "src"
            client = source_root / "p" / "Client.java"
            wrapper = source_root / "p" / "Wrapper.java"
            client.parent.mkdir(parents=True)
            original = (
                "package p;\n"
                "import java.awt.LayoutManager;\n"
                "import javax.swing.JComponent;\n"
                "public class Client {\n"
                "    public void wrap(JComponent component) {\n"
                "        final LayoutManager saved = component.getLayout();\n"
                "        component.setLayout(new Wrapper());\n"
                "    }\n"
                "}\n"
            )
            client.write_text(original, encoding="utf-8")
            wrapper.write_text(
                "package p;\n"
                "import java.awt.Component;\n"
                "import java.awt.Container;\n"
                "import java.awt.Dimension;\n"
                "import java.awt.LayoutManager;\n"
                "import javax.swing.JComponent;\n"
                "public class Wrapper implements LayoutManager {\n"
                "    Wrapper(LayoutManager saved, JComponent component) {}\n"
                "    public void addLayoutComponent(String name, Component comp) {}\n"
                "    public void removeLayoutComponent(Component comp) {}\n"
                "    public Dimension preferredLayoutSize(Container parent) { return new Dimension(); }\n"
                "    public Dimension minimumLayoutSize(Container parent) { return new Dimension(); }\n"
                "    public void layoutContainer(Container parent) {}\n"
                "}\n",
                encoding="utf-8",
            )

            report = normalize_procyon_source(source_root, jar)

            self.assertEqual(
                client.read_text(encoding="utf-8"),
                original,
            )
            self.assertEqual(
                report["summary"][
                    "hidden_layout_constructor_argument_reference_count"
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

    def test_linkedhashmap_field_placeholder_uses_exact_map_field(
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
                    "p/FolderMap.java": (
                        "package p;\n"
                        "import java.util.LinkedHashMap;\n"
                        "public class FolderMap "
                        "extends LinkedHashMap<String, Value> {}\n"
                    ),
                    "p/A.java": (
                        "package p;\n"
                        "import java.util.Set;\n"
                        "public class A {\n"
                        "    private final FolderMap folders = new FolderMap();\n"
                        "    public Value byKey(String key) {\n"
                        "        return folders.get(key);\n"
                        "    }\n"
                        "    public Set<String> keys() {\n"
                        "        return folders.keySet();\n"
                        "    }\n"
                        "    public void putValue(String key, Value value) {\n"
                        "        folders.put(key, value);\n"
                        "    }\n"
                        "    public void clearValues() {\n"
                        "        folders.clear();\n"
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
                "public class A {\n"
                "    private final FolderMap folders = new FolderMap();\n"
                "    public Value byKey(String key) {\n"
                "        return ((LinkedHashMap<K, Value>)this.folders).get(key);\n"
                "    }\n"
                "    public Set<String> keys() {\n"
                "        return ((LinkedHashMap<K, Value>)this.folders).keySet();\n"
                "    }\n"
                "    public void putValue(String key, Value value) {\n"
                "        ((LinkedHashMap<K, Value>)this.folders).put(key, value);\n"
                "    }\n"
                "    public void clearValues() {\n"
                "        ((LinkedHashMap<K, Value>)this.folders).clear();\n"
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
                    str(root / "before-map-field-placeholder"),
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
                "((LinkedHashMap<String, Value>)this.folders).get(key)",
                normalized,
            )
            self.assertIn(
                "((LinkedHashMap<String, Value>)this.folders).keySet()",
                normalized,
            )
            self.assertIn(
                "((LinkedHashMap<String, Value>)this.folders).put(key, value)",
                normalized,
            )
            self.assertIn(
                "((LinkedHashMap<String, Value>)this.folders).clear()",
                normalized,
            )

            actions = [
                row
                for row in report["actions"]
                if row["kind"] == "linkedhashmap_field_key_reconstruction"
            ]
            self.assertEqual(len(actions), 4)
            by_name = {row["method_name"]: row for row in actions}
            self.assertEqual(
                by_name["byKey"]["method_descriptor"],
                "(Ljava/lang/String;)Lp/Value;",
            )
            self.assertEqual(by_name["byKey"]["member_counts"], {"get": 1})
            self.assertEqual(by_name["keys"]["member_counts"], {"keySet": 1})
            self.assertEqual(by_name["putValue"]["member_counts"], {"put": 1})
            self.assertEqual(
                by_name["clearValues"]["member_counts"],
                {"clear": 1},
            )
            for action in actions:
                self.assertEqual(action["placeholder_counts"], {"K": 1})
                self.assertEqual(action["field_counts"], {"folders": 1})
                self.assertEqual(action["field_owners"], ["p/FolderMap"])
                self.assertEqual(
                    action["field_signatures"],
                    [
                        "Ljava/util/LinkedHashMap<"
                        "Ljava/lang/String;Lp/Value;>;"
                    ],
                )
                self.assertEqual(action["replacement_count"], 1)
            self.assertEqual(
                report["summary"][
                    "linkedhashmap_field_key_reconstruction_reference_count"
                ],
                4,
            )

            after = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "after-map-field-placeholder"),
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

    def test_linkedhashmap_field_placeholder_requires_map_subclass(
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
                    "p/NotMap.java": (
                        "package p;\n"
                        "public class NotMap {\n"
                        "    public Value get(Object key) { return new Value(); }\n"
                        "}\n"
                    ),
                    "p/A.java": (
                        "package p;\n"
                        "public class A {\n"
                        "    private final NotMap folders = new NotMap();\n"
                        "    public Value byKey(String key) {\n"
                        "        return folders.get(key);\n"
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
                "public class A {\n"
                "    private final NotMap folders = new NotMap();\n"
                "    public Value byKey(String key) {\n"
                "        return ((LinkedHashMap<K, Value>)this.folders).get(key);\n"
                "    }\n"
                "}\n"
            )
            source.write_text(original, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)

            self.assertEqual(source.read_text(encoding="utf-8"), original)
            self.assertEqual(
                report["summary"][
                    "linkedhashmap_field_key_reconstruction_reference_count"
                ],
                0,
            )

    def test_linkedhashmap_self_result_cast_moves_off_receiver(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "p/Item.java": (
                        "package p;\n"
                        "public class Item {}\n"
                    ),
                    "p/ItemList.java": (
                        "package p;\n"
                        "import java.util.ArrayList;\n"
                        "public class ItemList extends ArrayList<Item> {}\n"
                    ),
                    "p/Store.java": (
                        "package p;\n"
                        "import java.util.List;\n"
                        "public class Store {\n"
                        "    public void save(String key, List<Item> items) {}\n"
                        "}\n"
                    ),
                    "p/A.java": (
                        "package p;\n"
                        "import java.util.LinkedHashMap;\n"
                        "import java.util.List;\n"
                        "public class A extends LinkedHashMap<String, ItemList> {\n"
                        "    private final Store store = new Store();\n"
                        "    public void save(String key) {\n"
                        "        store.save(key, (List<Item>)this.get(key));\n"
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
                "import java.util.List;\n"
                "public class A extends LinkedHashMap<String, ItemList> {\n"
                "    private final Store store = new Store();\n"
                "    public void save(String key) {\n"
                "        store.save(key, "
                "((LinkedHashMap<K, List<Item>>)this).get(key));\n"
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
                    str(root / "before-linkedhashmap-result-cast"),
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(before.returncode, 0)

            report = normalize_procyon_source(root / "src", jar)
            normalized = source.read_text(encoding="utf-8")

            self.assertIn(
                "store.save(key, ((List<Item>)this.get(key)));",
                normalized,
            )
            self.assertNotIn(
                "LinkedHashMap<?, List<Item>",
                normalized,
            )
            actions = [
                row
                for row in report["actions"]
                if row["kind"] == "linkedhashmap_self_get_result_cast"
            ]
            self.assertEqual(len(actions), 1)
            self.assertEqual(actions[0]["method_name"], "save")
            self.assertEqual(
                actions[0]["method_descriptor"],
                "(Ljava/lang/String;)V",
            )
            self.assertEqual(
                actions[0]["result_types"],
                ["List<Item>"],
            )
            self.assertEqual(actions[0]["replacement_count"], 1)
            self.assertEqual(
                report["summary"][
                    "linkedhashmap_self_get_result_cast_reference_count"
                ],
                1,
            )

            after = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "after-linkedhashmap-result-cast"),
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



class ErasedMapNumberAssignmentTests(unittest.TestCase):
    def _fixture(self, root: Path, *, exact_drift: bool = False) -> Path:
        terminal = "byteValue" if exact_drift else "intValue"
        return _compile_java_fixture(
            root,
            {
                "p/A.java": (
                    "package p;\n"
                    "import java.util.Map;\n"
                    "public class A {\n"
                    "    public static int parse("
                    "Map<String, Object> map, String s) {\n"
                    "        Object value = map.get(s);\n"
                    "        if (!(value instanceof Number)) {\n"
                    "            throw new IllegalArgumentException();\n"
                    "        }\n"
                    f"        return ((Number)value).{terminal}();\n"
                    "    }\n"
                    "}\n"
                )
            },
        )

    def test_erased_map_number_assignment_restores_object_local(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._fixture(root)
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package p;\n"
                "import java.util.Map;\n"
                "public class A {\n"
                "    public static int parse("
                "Map<String, Object> map, String s) {\n"
                "        final Number value = map.get(s);\n"
                "        if (!(value instanceof Number)) {\n"
                "            throw new IllegalArgumentException();\n"
                "        }\n"
                "        return ((Number)value).intValue();\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )

            before = subprocess.run(
                ["javac", "-d", str(root / "before"), str(source)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(before.returncode, 0)

            report = normalize_procyon_source(root / "src", jar)
            normalized = source.read_text(encoding="utf-8")
            self.assertIn("final Object value = map.get(s);", normalized)
            action = next(
                row
                for row in report["actions"]
                if row["kind"]
                == "erased_map_number_assignment_reconstruction"
            )
            self.assertEqual(action["replacement_count"], 1)
            self.assertEqual(action["exact_object_local_slots"], [2])
            self.assertEqual(
                report["summary"][
                    "erased_map_number_assignment_reference_count"
                ],
                1,
            )

            after = subprocess.run(
                ["javac", "-d", str(root / "after"), str(source)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(after.returncode, 0, after.stderr)

    def test_erased_map_number_assignment_fails_closed_on_exact_drift(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._fixture(root, exact_drift=True)
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            malformed = (
                "package p;\n"
                "import java.util.Map;\n"
                "public class A {\n"
                "    public static int parse("
                "Map<String, Object> map, String s) {\n"
                "        final Number value = map.get(s);\n"
                "        if (!(value instanceof Number)) {\n"
                "            throw new IllegalArgumentException();\n"
                "        }\n"
                "        return ((Number)value).intValue();\n"
                "    }\n"
                "}\n"
            )
            source.write_text(malformed, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)
            self.assertEqual(source.read_text(encoding="utf-8"), malformed)
            self.assertFalse(
                any(
                    row["kind"]
                    == "erased_map_number_assignment_reconstruction"
                    for row in report["actions"]
                )
            )


if __name__ == "__main__":
    unittest.main()

# R8M exact-v308 acceptance is recorded on PR #114; keep this test surface CI-bound.

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



def _patch_bridge_invoke_methodref(
    class_bytes: bytes,
    *,
    bridge_name: str,
    bridge_descriptor: str,
    target_owner: str,
    target_name: str,
    target_descriptor: str,
) -> bytes:
    data = bytearray(class_bytes)

    def u2_at(offset: int) -> int:
        return struct.unpack_from(">H", data, offset)[0]

    def u4_at(offset: int) -> int:
        return struct.unpack_from(">I", data, offset)[0]

    cp_count = u2_at(8)
    offset = 10
    utf8: dict[int, str] = {}
    classes: dict[int, int] = {}
    name_and_types: dict[int, tuple[int, int]] = {}
    methodrefs: dict[int, tuple[int, int]] = {}
    index = 1
    while index < cp_count:
        tag = data[offset]
        offset += 1
        if tag == 1:
            length = u2_at(offset)
            offset += 2
            utf8[index] = bytes(data[offset:offset + length]).decode("utf-8")
            offset += length
        elif tag in {3, 4}:
            offset += 4
        elif tag in {5, 6}:
            offset += 8
            index += 1
        elif tag == 7:
            classes[index] = u2_at(offset)
            offset += 2
        elif tag == 8:
            offset += 2
        elif tag in {9, 10, 11}:
            class_index = u2_at(offset)
            nat_index = u2_at(offset + 2)
            if tag == 10:
                methodrefs[index] = (class_index, nat_index)
            offset += 4
        elif tag == 12:
            name_and_types[index] = (u2_at(offset), u2_at(offset + 2))
            offset += 4
        elif tag == 15:
            offset += 3
        elif tag == 16:
            offset += 2
        elif tag in {17, 18}:
            offset += 4
        elif tag in {19, 20}:
            offset += 2
        else:
            raise AssertionError(f"unsupported constant-pool tag {tag}")
        index += 1

    def methodref_identity(cp_index: int) -> tuple[str, str, str] | None:
        ref = methodrefs.get(cp_index)
        if ref is None:
            return None
        class_index, nat_index = ref
        class_name_index = classes.get(class_index)
        nat = name_and_types.get(nat_index)
        if class_name_index is None or nat is None:
            return None
        name_index, descriptor_index = nat
        return (
            utf8.get(class_name_index, ""),
            utf8.get(name_index, ""),
            utf8.get(descriptor_index, ""),
        )

    target_indexes = [
        cp_index
        for cp_index in methodrefs
        if methodref_identity(cp_index)
        == (target_owner, target_name, target_descriptor)
    ]
    if len(target_indexes) != 1:
        raise AssertionError(
            f"expected one target Methodref, found {target_indexes}"
        )
    target_index = target_indexes[0]

    cursor = offset
    cursor += 6
    interfaces_count = u2_at(cursor)
    cursor += 2 + 2 * interfaces_count

    fields_count = u2_at(cursor)
    cursor += 2
    for _ in range(fields_count):
        cursor += 6
        attribute_count = u2_at(cursor)
        cursor += 2
        for _ in range(attribute_count):
            cursor += 2
            length = u4_at(cursor)
            cursor += 4 + length

    methods_count = u2_at(cursor)
    cursor += 2
    patched = 0
    for _ in range(methods_count):
        access = u2_at(cursor)
        name_index = u2_at(cursor + 2)
        descriptor_index = u2_at(cursor + 4)
        attribute_count = u2_at(cursor + 6)
        cursor += 8
        name = utf8.get(name_index, "")
        descriptor = utf8.get(descriptor_index, "")

        for _ in range(attribute_count):
            attribute_name_index = u2_at(cursor)
            length = u4_at(cursor + 2)
            payload = cursor + 6
            attribute_name = utf8.get(attribute_name_index, "")
            if (
                name == bridge_name
                and descriptor == bridge_descriptor
                and (access & 0x1000)
                and (access & 0x0040)
                and attribute_name == "Code"
            ):
                code_length = u4_at(payload + 4)
                code_start = payload + 8
                code_end = code_start + code_length
                invoke_offsets = [
                    pos
                    for pos in range(code_start, code_end - 2)
                    if data[pos] == 0xB6
                ]
                if len(invoke_offsets) != 1:
                    raise AssertionError(
                        f"expected one bridge invokevirtual, found {invoke_offsets}"
                    )
                pos = invoke_offsets[0]
                struct.pack_into(">H", data, pos + 1, target_index)
                patched += 1
            cursor = payload + length

    if patched != 1:
        raise AssertionError(f"expected one patched bridge, got {patched}")
    return bytes(data)


def _synthetic_bridge_forwarder_fixture(
    root: Path,
    *,
    retarget_bridge: bool,
) -> Path:
    jar = _compile_java_fixture(
        root,
        {
            "p/Base.java": (
                "package p;\n"
                "import java.util.Map;\n"
                "public abstract class Base<T> {\n"
                "    public abstract T a(int id, Map<String,Object> values);\n"
                "}\n"
            ),
            "p/R.java": (
                "package p;\n"
                "public class R {}\n"
            ),
            "p/F.java": (
                "package p;\n"
                "import java.util.Map;\n"
                "public class F extends Base<R> {\n"
                "    public R a(int id, Map<String,Object> values) {\n"
                "        return b(id, values);\n"
                "    }\n"
                "    public R b(int id, Map<String,Object> values) {\n"
                "        return new R();\n"
                "    }\n"
                "}\n"
            ),
        },
    )
    if not retarget_bridge:
        return jar

    patched = root / "synthetic-bridge-readable.jar"
    bridge_descriptor = "(ILjava/util/Map;)Ljava/lang/Object;"
    target_descriptor = "(ILjava/util/Map;)Lp/R;"
    with zipfile.ZipFile(jar) as source_zip, zipfile.ZipFile(
        patched, "w"
    ) as target_zip:
        for info in source_zip.infolist():
            payload = source_zip.read(info.filename)
            if info.filename == "p/F.class":
                payload = _patch_bridge_invoke_methodref(
                    payload,
                    bridge_name="a",
                    bridge_descriptor=bridge_descriptor,
                    target_owner="p/F",
                    target_name="b",
                    target_descriptor=target_descriptor,
                )
            target_zip.writestr(info, payload)
    return patched

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

    def test_reference_field_shadowed_self_static_owner_in_instance_method_is_qualified(
        self,
    ):
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
                        "    public int read() {\n"
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
                "    public int read() {\n"
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
                    str(root / "before-reference-instance-classes"),
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(before.returncode, 0)

            report = normalize_procyon_source(root / "src", jar)
            normalized = source.read_text(encoding="utf-8")
            self.assertIn("return pkg.q.a + pkg.q.f;", normalized)

            action = next(
                row
                for row in report["actions"]
                if (
                    row["kind"]
                    == "reference_shadowed_self_static_field_owner_qualification"
                    and row["method_name"] == "read"
                )
            )
            self.assertEqual(action["method_descriptor"], "()I")
            self.assertEqual(action["reference_shadow_owners"], ["pkg/q"])
            self.assertEqual(
                action["field_access_counts"],
                {"pkg/q.a": 1, "pkg/q.f": 1},
            )
            self.assertEqual(action["replacement_count"], 2)
            self.assertEqual(
                action["provenance"]["strategy"],
                "exact_instance_method_complete_field_access_qualification",
            )

            after = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "after-reference-instance-classes"),
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

    def test_reference_field_shadowed_self_instance_count_mismatch_fails_closed(
        self,
    ):
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
                        "    public int read() { return pkg.q.a; }\n"
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
                "    public int read() { return q.a + q.a; }\n"
                "}\n"
            )
            source.write_text(original, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)

            self.assertEqual(source.read_text(encoding="utf-8"), original)
            self.assertFalse(
                any(
                    row["kind"]
                    == "reference_shadowed_self_static_field_owner_qualification"
                    and row["method_name"] == "read"
                    for row in report["actions"]
                )
            )

    def test_reference_field_shadowed_self_static_owner_in_constructor_is_qualified(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "pkg/Base.java": (
                        "package pkg;\n"
                        "public class Base {\n"
                        "    protected String q;\n"
                        "    public Base(String a, String b) {}\n"
                        "}\n"
                    ),
                    "pkg/q.java": (
                        "package pkg;\n"
                        "public class q extends Base {\n"
                        "    public static String a = \"a\";\n"
                        "    public static String b = \"b\";\n"
                        "    public q() { super(pkg.q.a, pkg.q.b); }\n"
                        "}\n"
                    ),
                },
            )
            source = root / "src" / "pkg" / "q.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package pkg;\n"
                "public class q extends Base {\n"
                "    public static String a = \"a\";\n"
                "    public static String b = \"b\";\n"
                "    public q() { super(q.a, q.b); }\n"
                "}\n",
                encoding="utf-8",
            )

            before = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "before-reference-constructor-classes"),
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
                "super(pkg.q.a, pkg.q.b);",
                normalized,
            )
            action = next(
                row
                for row in report["actions"]
                if (
                    row["kind"]
                    == "reference_shadowed_self_static_field_owner_qualification"
                    and row["method_name"] == "<init>"
                )
            )
            self.assertEqual(action["method_descriptor"], "()V")
            self.assertEqual(action["reference_shadow_owners"], ["pkg/Base"])
            self.assertEqual(
                action["field_access_counts"],
                {"pkg/q.a": 1, "pkg/q.b": 1},
            )
            self.assertEqual(action["replacement_count"], 2)

            after = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "after-reference-constructor-classes"),
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

    def test_reference_field_shadowed_constructor_count_mismatch_fails_closed(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "pkg/Base.java": (
                        "package pkg;\n"
                        "public class Base {\n"
                        "    protected String q;\n"
                        "    public Base(String a, String b) {}\n"
                        "}\n"
                    ),
                    "pkg/q.java": (
                        "package pkg;\n"
                        "public class q extends Base {\n"
                        "    public static String a = \"a\";\n"
                        "    public q() { super(pkg.q.a, \"fixed\"); }\n"
                        "}\n"
                    ),
                },
            )
            source = root / "src" / "pkg" / "q.java"
            source.parent.mkdir(parents=True)
            original = (
                "package pkg;\n"
                "public class q extends Base {\n"
                "    public static String a = \"a\";\n"
                "    public q() { super(q.a, q.a); }\n"
                "}\n"
            )
            source.write_text(original, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)

            self.assertEqual(source.read_text(encoding="utf-8"), original)
            self.assertFalse(
                any(
                    row["kind"]
                    == "reference_shadowed_self_static_field_owner_qualification"
                    and row["method_name"] == "<init>"
                    for row in report["actions"]
                )
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

    def test_reference_field_shadowed_self_static_owner_in_clinit_is_qualified(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "pkg/q.java": (
                        "package pkg;\n"
                        "public class q {\n"
                        "    public String q;\n"
                        "    public static int a;\n"
                        "    public static int f;\n"
                        "    static { pkg.q.a = 1; pkg.q.f = 2; }\n"
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
                "    public static int a;\n"
                "    public static int f;\n"
                "    static { q.a = 1; q.f = 2; }\n"
                "}\n",
                encoding="utf-8",
            )

            before = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "before-reference-clinit-classes"),
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
            self.assertIn(
                "static { pkg.q.a = 1; pkg.q.f = 2; }",
                normalized,
            )

            action = next(
                row
                for row in report["actions"]
                if (
                    row["kind"]
                    == "reference_shadowed_self_static_field_owner_qualification"
                    and row["method_name"] == "<clinit>"
                )
            )
            self.assertEqual(action["method_descriptor"], "()V")
            self.assertEqual(action["reference_shadow_owners"], ["pkg/q"])
            self.assertEqual(
                action["field_access_counts"],
                {"pkg/q.a": 1, "pkg/q.f": 1},
            )
            self.assertEqual(action["replacement_count"], 2)

            after = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "after-reference-clinit-classes"),
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

    def test_reference_field_shadowed_self_clinit_count_mismatch_fails_closed(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "pkg/q.java": (
                        "package pkg;\n"
                        "public class q {\n"
                        "    public String q;\n"
                        "    public static int a;\n"
                        "    static { pkg.q.a = 1; }\n"
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
                "    public static int a;\n"
                "    static { q.a = 1; q.a = 2; }\n"
                "}\n"
            )
            source.write_text(original, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)

            self.assertEqual(source.read_text(encoding="utf-8"), original)
            self.assertFalse(
                any(
                    row["kind"]
                    == "reference_shadowed_self_static_field_owner_qualification"
                    and row["method_name"] == "<clinit>"
                    for row in report["actions"]
                )
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

    def test_nested_type_static_field_shadow_in_clinit_forces_type_context(
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
                        "    public static int value;\n"
                        "    static {\n"
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
                "    public static int value;\n"
                "    static {\n"
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
                    str(root / "before-clinit-classes"),
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
                    and row.get("method_name") == "<clinit>"
                )
            )
            self.assertEqual(action["method_descriptor"], "()V")
            self.assertEqual(action["nested_owners"], ["pkg/Outer$b"])
            self.assertEqual(action["replacement_count"], 2)
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
                    str(root / "after-clinit-classes"),
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

    def test_nested_type_static_field_shadow_in_clinit_count_mismatch_fails_closed(
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
                        "    }\n"
                        "}\n"
                    ),
                    "use/Current.java": (
                        "package use;\n"
                        "public class Current {\n"
                        "    public static int value;\n"
                        "    static { value = ((pkg.Outer.b)null).h; }\n"
                        "}\n"
                    ),
                },
            )

            source = root / "src" / "use" / "Current.java"
            source.parent.mkdir(parents=True)
            original = (
                "package use;\n"
                "public class Current {\n"
                "    public static int value;\n"
                "    static { value = pkg.Outer.b.h + pkg.Outer.b.h; }\n"
                "}\n"
            )
            source.write_text(original, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)

            self.assertEqual(source.read_text(encoding="utf-8"), original)
            self.assertFalse(
                any(
                    row["kind"]
                    == "shadowed_nested_static_field_owner_type_context"
                    and row.get("method_name") == "<clinit>"
                    for row in report["actions"]
                )
            )

    def test_exact_static_call_infers_nested_type_collision_owner(
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
                        "    public static int a = 7;\n"
                        "    public static class a {\n"
                        "        public static final a d = new a();\n"
                        "    }\n"
                        "    public static void use(a mode, byte[] x, byte[] y) {}\n"
                        "}\n"
                    ),
                    "use/Current.java": (
                        "package use;\n"
                        "import dep.r;\n"
                        "public class Current {\n"
                        "    public void load(byte[] x, byte[] y) {\n"
                        "        r.use(((dep.r.a)null).d, x, y);\n"
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
                "    public void load(byte[] x, byte[] y) {\n"
                "        r.use(r.a.d, x, y);\n"
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
                    str(root / "before-exact-nested-collision"),
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
                "r.use(((dep.r.a)null).d, x, y);",
                normalized,
            )
            action = next(
                row
                for row in report["actions"]
                if row["kind"]
                == "exact_static_call_nested_type_collision_reconstruction"
            )
            self.assertEqual(action["replacement_count"], 1)
            self.assertEqual(action["groups"][0]["exact_outer"], "dep/r")
            self.assertEqual(action["groups"][0]["nested_owner"], "dep/r$a")
            self.assertEqual(
                action["groups"][0]["shadow_declaring_owners"],
                ["dep/r"],
            )
            self.assertEqual(
                report["summary"][
                    "exact_static_call_nested_type_collision_action_count"
                ],
                1,
            )
            self.assertEqual(
                report["summary"][
                    "exact_static_call_nested_type_collision_reference_count"
                ],
                1,
            )

            after = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "after-exact-nested-collision"),
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

    def test_exact_static_call_nested_collision_count_drift_fails_closed(
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
                        "    public static int a = 7;\n"
                        "    public static class a {\n"
                        "        public static final a d = new a();\n"
                        "    }\n"
                        "    public static void use(a mode, byte[] x, byte[] y) {}\n"
                        "}\n"
                    ),
                    "use/Current.java": (
                        "package use;\n"
                        "import dep.r;\n"
                        "public class Current {\n"
                        "    public void load(byte[] x, byte[] y) {\n"
                        "        r.use(((dep.r.a)null).d, x, y);\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )
            source = root / "src" / "use" / "Current.java"
            source.parent.mkdir(parents=True)
            original = (
                "package use;\n"
                "import dep.r;\n"
                "public class Current {\n"
                "    public void load(byte[] x, byte[] y) {\n"
                "        r.use(r.a.d, x, y);\n"
                "        r.use(r.a.d, x, y);\n"
                "    }\n"
                "}\n"
            )
            source.write_text(original, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)

            self.assertEqual(source.read_text(encoding="utf-8"), original)
            self.assertEqual(
                report["summary"][
                    "exact_static_call_nested_type_collision_reference_count"
                ],
                0,
            )

    def test_exact_static_call_without_nested_name_collision_fails_closed(
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
                        "    public static class a {\n"
                        "        public static final a d = new a();\n"
                        "    }\n"
                        "    public static void use(a mode, byte[] x, byte[] y) {}\n"
                        "}\n"
                    ),
                    "use/Current.java": (
                        "package use;\n"
                        "import dep.r;\n"
                        "public class Current {\n"
                        "    public void load(byte[] x, byte[] y) {\n"
                        "        r.use(((dep.r.a)null).d, x, y);\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )
            source = root / "src" / "use" / "Current.java"
            source.parent.mkdir(parents=True)
            original = (
                "package use;\n"
                "import dep.r;\n"
                "public class Current {\n"
                "    public void load(byte[] x, byte[] y) {\n"
                "        r.use(r.a.d, x, y);\n"
                "    }\n"
                "}\n"
            )
            source.write_text(original, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)

            self.assertEqual(source.read_text(encoding="utf-8"), original)
            self.assertEqual(
                report["summary"][
                    "exact_static_call_nested_type_collision_action_count"
                ],
                0,
            )

    def test_nested_type_static_method_shadow_in_ordinary_method_forces_type_context(
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
                        "        public static int a(String s) {\n"
                        "            return s.length();\n"
                        "        }\n"
                        "    }\n"
                        "}\n"
                    ),
                    "use/Current.java": (
                        "package use;\n"
                        "public class Current {\n"
                        "    public static int m(String s) {\n"
                        "        return ((pkg.Outer.b)null).a(s);\n"
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
                "    public static int m(String s) {\n"
                "        return pkg.Outer.b.a(s);\n"
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
                    str(root / "before-nested-method-ordinary"),
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
                "return ((pkg.Outer.b)null).a(s);",
                normalized,
            )
            action = next(
                row
                for row in report["actions"]
                if (
                    row["kind"]
                    == "shadowed_nested_static_method_owner_type_context"
                    and row["method_name"] == "m"
                )
            )
            self.assertEqual(
                action["method_descriptor"],
                "(Ljava/lang/String;)I",
            )
            self.assertEqual(action["nested_owners"], ["pkg/Outer$b"])
            self.assertEqual(
                action["method_invocation_counts"],
                {"pkg/Outer$b.a": 1},
            )
            self.assertEqual(action["replacement_count"], 1)

            after = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "after-nested-method-ordinary"),
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

    def test_nested_type_static_method_shadow_in_ordinary_method_count_mismatch_fails_closed(
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
                        "        public static int a(String s) {\n"
                        "            return s.length();\n"
                        "        }\n"
                        "    }\n"
                        "}\n"
                    ),
                    "use/Current.java": (
                        "package use;\n"
                        "public class Current {\n"
                        "    public static int m(String s) {\n"
                        "        return ((pkg.Outer.b)null).a(s);\n"
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
                "    public static int m(String s) {\n"
                "        return pkg.Outer.b.a(s)"
                " + pkg.Outer.b.a(s);\n"
                "    }\n"
                "}\n"
            )
            source.write_text(original, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)

            self.assertEqual(source.read_text(encoding="utf-8"), original)
            self.assertFalse(
                any(
                    row["kind"]
                    == "shadowed_nested_static_method_owner_type_context"
                    and row["method_name"] == "m"
                    for row in report["actions"]
                )
            )

    def test_nested_type_static_method_shadow_in_clinit_forces_type_context(
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
                        "        public static int a() { return 7; }\n"
                        "    }\n"
                        "}\n"
                    ),
                    "use/Current.java": (
                        "package use;\n"
                        "public class Current {\n"
                        "    public static int value;\n"
                        "    static {\n"
                        "        value = ((pkg.Outer.b)null).a();\n"
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
                "    public static int value;\n"
                "    static {\n"
                "        value = pkg.Outer.b.a();\n"
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
                    str(root / "before-clinit-method-classes"),
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(before.returncode, 0)

            report = normalize_procyon_source(root / "src", jar)
            normalized = source.read_text(encoding="utf-8")

            self.assertIn("((pkg.Outer.b)null).a()", normalized)
            action = next(
                row
                for row in report["actions"]
                if row["kind"]
                == "shadowed_nested_static_method_owner_type_context"
            )
            self.assertEqual(action["method_name"], "<clinit>")
            self.assertEqual(action["method_descriptor"], "()V")
            self.assertEqual(action["nested_owners"], ["pkg/Outer$b"])
            self.assertEqual(
                action["method_invocation_counts"],
                {"pkg/Outer$b.a": 1},
            )
            self.assertEqual(action["replacement_count"], 1)
            self.assertEqual(
                report["summary"][
                    "shadowed_nested_static_method_action_count"
                ],
                1,
            )
            self.assertEqual(
                report["summary"][
                    "shadowed_nested_static_method_reference_count"
                ],
                1,
            )

            after = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "after-clinit-method-classes"),
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

    def test_nested_type_static_method_shadow_in_clinit_count_mismatch_fails_closed(
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
                        "        public static int a() { return 7; }\n"
                        "    }\n"
                        "}\n"
                    ),
                    "use/Current.java": (
                        "package use;\n"
                        "public class Current {\n"
                        "    public static int value;\n"
                        "    static { value = ((pkg.Outer.b)null).a(); }\n"
                        "}\n"
                    ),
                },
            )

            source = root / "src" / "use" / "Current.java"
            source.parent.mkdir(parents=True)
            original = (
                "package use;\n"
                "public class Current {\n"
                "    public static int value;\n"
                "    static { value = pkg.Outer.b.a() + pkg.Outer.b.a(); }\n"
                "}\n"
            )
            source.write_text(original, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)

            self.assertEqual(source.read_text(encoding="utf-8"), original)
            self.assertEqual(
                report["summary"][
                    "shadowed_nested_static_method_reference_count"
                ],
                0,
            )

    def test_same_package_outer_nested_static_owners_in_clinit(
        self,
    ):
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
                        "        public static int h = 7;\n"
                        "        public static int a() { return 8; }\n"
                        "    }\n"
                        "}\n"
                    ),
                    "p/Current.java": (
                        "package p;\n"
                        "public class Current {\n"
                        "    public static int value;\n"
                        "    static {\n"
                        "        value = ((p.Outer.b)null).h"
                        " + ((p.Outer.b)null).a();\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )

            source = root / "src" / "p" / "Current.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package p;\n"
                "public class Current {\n"
                "    public static int value;\n"
                "    static {\n"
                "        value = Outer.b.h + Outer.b.a();\n"
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
                    str(root / "before-same-package-nested-clinit"),
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(before.returncode, 0)

            report = normalize_procyon_source(root / "src", jar)
            normalized = source.read_text(encoding="utf-8")

            self.assertIn("((p.Outer.b)null).h", normalized)
            self.assertIn("((p.Outer.b)null).a()", normalized)

            field_action = next(
                row
                for row in report["actions"]
                if (
                    row["kind"]
                    == "shadowed_nested_static_field_owner_type_context"
                    and row.get("method_name") == "<clinit>"
                )
            )
            self.assertEqual(field_action["nested_owners"], ["p/Outer$b"])
            self.assertEqual(
                field_action["field_access_counts"],
                {"p/Outer$b.h": 1},
            )

            method_action = next(
                row
                for row in report["actions"]
                if row["kind"]
                == "shadowed_nested_static_method_owner_type_context"
            )
            self.assertEqual(method_action["nested_owners"], ["p/Outer$b"])
            self.assertEqual(
                method_action["method_invocation_counts"],
                {"p/Outer$b.a": 1},
            )

            after = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "after-same-package-nested-clinit"),
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

    def test_imported_outer_nested_static_field_shadow_uses_exact_owner(
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
                        "    public static class a {\n"
                        "        public static final a d = new a();\n"
                        "    }\n"
                        "    public static void use(a mode, byte[] x, byte[] y) {}\n"
                        "}\n"
                    ),
                    "use/Current.java": (
                        "package use;\n"
                        "import dep.r;\n"
                        "public class Current {\n"
                        "    public int r;\n"
                        "    public void load(byte[] x, byte[] y) {\n"
                        "        dep.r.use(dep.r.a.d, x, y);\n"
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
                "    public int r;\n"
                "    public void load(byte[] x, byte[] y) {\n"
                "        r.use(r.a.d, x, y);\n"
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
                    str(root / "before-imported-outer-nested-field"),
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
                "dep.r.use(((dep.r.a)null).d, x, y);",
                normalized,
            )

            action = next(
                row
                for row in report["actions"]
                if row["kind"]
                == "shadowed_imported_outer_nested_static_field_owner_type_context"
            )
            self.assertEqual(action["imported_owners"], ["dep/r"])
            self.assertEqual(action["nested_owners"], ["dep/r$a"])
            self.assertEqual(
                action["field_access_counts"],
                {"dep/r$a.d": 1},
            )
            self.assertEqual(action["replacement_count"], 1)
            self.assertEqual(
                report["summary"][
                    "shadowed_imported_outer_nested_static_field_reference_count"
                ],
                1,
            )

            after = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "after-imported-outer-nested-field"),
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

    def test_imported_outer_nested_static_field_shadow_is_scope_bounded(
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
                        "    public static class a {\n"
                        "        public static int d = 7;\n"
                        "    }\n"
                        "}\n"
                    ),
                    "use/Current.java": (
                        "package use;\n"
                        "import dep.r;\n"
                        "public class Current {\n"
                        "    public static int load(boolean flag) {\n"
                        "        if (flag) {\n"
                        "            byte[] r = null;\n"
                        "            return dep.r.a.d;\n"
                        "        }\n"
                        "        return dep.r.a.d;\n"
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
                "    public static int load(boolean flag) {\n"
                "        if (flag) {\n"
                "            byte[] r = null;\n"
                "            return r.a.d;\n"
                "        }\n"
                "        return dep.r.a.d;\n"
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
                    str(root / "before-imported-outer-nested-scope"),
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
                "return ((dep.r.a)null).d;",
                normalized,
            )
            self.assertIn(
                "return dep.r.a.d;",
                normalized,
            )
            action = next(
                row
                for row in report["actions"]
                if row["kind"]
                == "shadowed_imported_outer_nested_static_field_owner_type_context"
            )
            self.assertEqual(
                action["reference_local_shadow_scope_count"],
                1,
            )
            self.assertEqual(action["replacement_count"], 1)

            after = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "after-imported-outer-nested-scope"),
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

    def test_imported_outer_nested_static_field_shadow_fails_on_count_drift(
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
                        "    public static class a {\n"
                        "        public static final int d = 7;\n"
                        "    }\n"
                        "}\n"
                    ),
                    "use/Current.java": (
                        "package use;\n"
                        "import dep.r;\n"
                        "public class Current {\n"
                        "    public int r;\n"
                        "    public int load() { return dep.r.a.d; }\n"
                        "}\n"
                    ),
                },
            )
            source = root / "src" / "use" / "Current.java"
            source.parent.mkdir(parents=True)
            original = (
                "package use;\n"
                "import dep.r;\n"
                "public class Current {\n"
                "    public int r;\n"
                "    public int load() { return r.a.d + r.a.d; }\n"
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
                    "shadowed_imported_outer_nested_static_field_reference_count"
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


    def test_intpredicate_parameter_capture_alias_uses_exact_parameter_slot(
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
                        "    public boolean contains(int target) {\n"
                        "        return Arrays.stream(new int[] {1, 2, 3})\n"
                        "            .anyMatch(value -> value == target);\n"
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
                "    public boolean contains(int target) {\n"
                "        return Arrays.stream(new int[] {1, 2, 3})\n"
                "            .anyMatch(value -> value == n5);\n"
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
                    str(root / "before-intpredicate-param"),
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
                ".anyMatch(value -> value == target);",
                normalized,
            )
            self.assertNotIn("n5", normalized)

            action = next(
                row
                for row in report["actions"]
                if row["kind"]
                == "intpredicate_parameter_capture_alias"
            )
            self.assertEqual(action["captured_parameter_name"], "target")
            self.assertEqual(action["undeclared_capture_alias"], "n5")
            self.assertEqual(action["lambda_parameter_name"], "value")
            self.assertEqual(action["capture_slot"], 1)
            self.assertEqual(action["replacement_count"], 1)
            self.assertEqual(
                report["summary"][
                    "intpredicate_parameter_capture_alias_action_count"
                ],
                1,
            )
            self.assertEqual(
                report["summary"][
                    "intpredicate_parameter_capture_alias_reference_count"
                ],
                1,
            )

            after = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "after-intpredicate-param"),
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

    def test_intpredicate_parameter_capture_alias_rejects_local_capture(
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
                        "    public boolean contains(int packed) {\n"
                        "        int local = packed >>> 16;\n"
                        "        return Arrays.stream(new int[] {1, 2, 3})\n"
                        "            .anyMatch(value -> value == local);\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            original = (
                "package p;\n"
                "import java.util.Arrays;\n"
                "public class A {\n"
                "    public boolean contains(int packed) {\n"
                "        int local = packed >>> 16;\n"
                "        return Arrays.stream(new int[] {1, 2, 3})\n"
                "            .anyMatch(value -> value == n8);\n"
                "    }\n"
                "}\n"
            )
            source.write_text(original, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)

            self.assertEqual(source.read_text(encoding="utf-8"), original)
            self.assertEqual(
                report["summary"][
                    "intpredicate_parameter_capture_alias_action_count"
                ],
                0,
            )
            self.assertEqual(
                report["summary"][
                    "intpredicate_parameter_capture_alias_reference_count"
                ],
                0,
            )

    def test_intpredicate_parameter_capture_alias_rejects_non_equality_helper(
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
                        "    public boolean contains(int target) {\n"
                        "        return Arrays.stream(new int[] {1, 2, 3})\n"
                        "            .anyMatch(value -> value < target);\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            original = (
                "package p;\n"
                "import java.util.Arrays;\n"
                "public class A {\n"
                "    public boolean contains(int target) {\n"
                "        return Arrays.stream(new int[] {1, 2, 3})\n"
                "            .anyMatch(value -> value == n5);\n"
                "    }\n"
                "}\n"
            )
            source.write_text(original, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)

            self.assertEqual(source.read_text(encoding="utf-8"), original)
            self.assertEqual(
                report["summary"][
                    "intpredicate_parameter_capture_alias_action_count"
                ],
                0,
            )
            self.assertEqual(
                report["summary"][
                    "intpredicate_parameter_capture_alias_reference_count"
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


    def test_impossible_collectors_tolist_cast_uses_exact_generic_authority(
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
                        "import java.util.List;\n"
                        "import java.util.stream.Collectors;\n"
                        "public class A {\n"
                        "    public static List<String> values(String prefix) {\n"
                        "        return Arrays.asList(\"a\", \"ab\").stream()\n"
                        "            .filter(value -> value.startsWith(prefix))\n"
                        "            .collect(Collectors.toList());\n"
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
                "import java.util.List;\n"
                "import java.util.stream.Collector;\n"
                "import java.util.stream.Collectors;\n"
                "public class A {\n"
                "    public static List<String> values(String prefix) {\n"
                "        return Arrays.asList(\"a\", \"ab\").stream()\n"
                "            .filter(value -> value.startsWith(prefix))\n"
                "            .collect((Collector<? super Object, ?, List<String>>)Collectors.toList());\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )

            before = subprocess.run(
                [
                    "javac",
                    "-d",
                    str(root / "before-collector-cast"),
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(before.returncode, 0)

            report = normalize_procyon_source(root / "src", jar)
            normalized = source.read_text(encoding="utf-8")
            self.assertIn(".collect(Collectors.toList())", normalized)
            self.assertNotIn(
                "Collector<? super Object, ?, List<String>>",
                normalized,
            )

            action = next(
                row
                for row in report["actions"]
                if row["kind"]
                == "impossible_collectors_tolist_cast_removal"
            )
            self.assertEqual(action["element_owner"], "java/lang/String")
            self.assertEqual(
                action["method_signature"],
                "(Ljava/lang/String;)Ljava/util/List<Ljava/lang/String;>;",
            )
            self.assertEqual(action["replacement_count"], 1)

            after = subprocess.run(
                [
                    "javac",
                    "-d",
                    str(root / "after-collector-cast"),
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

    def test_impossible_collectors_tolist_cast_rejects_qualified_element_owner_drift(
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
                        "import java.util.List;\n"
                        "import java.util.stream.Collectors;\n"
                        "public class A {\n"
                        "    public static List<String> values(String prefix) {\n"
                        "        return Arrays.asList(\"a\", \"ab\").stream()\n"
                        "            .filter(value -> value.startsWith(prefix))\n"
                        "            .collect(Collectors.toList());\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            original = (
                "package p;\n"
                "import java.util.Arrays;\n"
                "import java.util.List;\n"
                "import java.util.stream.Collector;\n"
                "import java.util.stream.Collectors;\n"
                "public class A {\n"
                "    public static List<String> values(String prefix) {\n"
                "        return Arrays.asList(\"a\", \"ab\").stream()\n"
                "            .filter(value -> value.startsWith(prefix))\n"
                "            .collect((Collector<? super Object, ?, List<other.String>>)Collectors.toList());\n"
                "    }\n"
                "}\n"
            )
            source.write_text(original, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)

            self.assertEqual(source.read_text(encoding="utf-8"), original)
            self.assertEqual(
                report["summary"][
                    "impossible_collectors_tolist_cast_action_count"
                ],
                0,
            )

    def test_impossible_collectors_tolist_cast_fails_on_generic_return_drift(
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
                        "import java.util.List;\n"
                        "import java.util.stream.Collectors;\n"
                        "public class A {\n"
                        "    public static List<Object> values(String prefix) {\n"
                        "        return Arrays.<Object>asList(\"a\", \"ab\").stream()\n"
                        "            .filter(value -> value instanceof String)\n"
                        "            .collect(Collectors.toList());\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            original = (
                "package p;\n"
                "import java.util.Arrays;\n"
                "import java.util.List;\n"
                "import java.util.stream.Collector;\n"
                "import java.util.stream.Collectors;\n"
                "public class A {\n"
                "    public static List<String> values(String prefix) {\n"
                "        return Arrays.asList(\"a\", \"ab\").stream()\n"
                "            .filter(value -> value.startsWith(prefix))\n"
                "            .collect((Collector<? super Object, ?, List<String>>)Collectors.toList());\n"
                "    }\n"
                "}\n"
            )
            source.write_text(original, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)

            self.assertEqual(source.read_text(encoding="utf-8"), original)
            self.assertEqual(
                report["summary"][
                    "impossible_collectors_tolist_cast_action_count"
                ],
                0,
            )

    def test_invokedynamic_captured_class_local_alias_uses_exact_helper(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "p/D.java": (
                        "package p;\n"
                        "public class D {\n"
                        "    public D(String value) {}\n"
                        "}\n"
                    ),
                    "p/A.java": (
                        "package p;\n"
                        "import java.util.Arrays;\n"
                        "import java.util.List;\n"
                        "import java.util.stream.Collectors;\n"
                        "public class A {\n"
                        "    public List<D> scan(Object value) {\n"
                        "        Class<?> clazz = value.getClass();\n"
                        "        return Arrays.stream(clazz.getDeclaredFields())\n"
                        "            .map(field -> {\n"
                        "                try {\n"
                        "                    return new D(String.valueOf("
                        "field.get(clazz)));\n"
                        "                } catch (IllegalAccessException ex) {\n"
                        "                    System.err.println("
                        "clazz.getSimpleName() + field.getName());\n"
                        "                    return null;\n"
                        "                }\n"
                        "            })\n"
                        "            .collect(Collectors.toList());\n"
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
                "import java.util.List;\n"
                "import java.util.stream.Collectors;\n"
                "public class A {\n"
                "    public List<D> scan(Object value) {\n"
                "        Class<?> clazz = value.getClass();\n"
                "        return Arrays.stream(clazz.getDeclaredFields())\n"
                "            .map(field -> {\n"
                "                try {\n"
                "                    return new D(String.valueOf("
                "field.get(obj)));\n"
                "                } catch (IllegalAccessException ex) {\n"
                "                    System.err.println("
                "obj.getSimpleName() + field.getName());\n"
                "                    return null;\n"
                "                }\n"
                "            })\n"
                "            .collect(Collectors.toList());\n"
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
                    str(root / "before-captured-class-alias"),
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(before.returncode, 0)

            report = normalize_procyon_source(root / "src", jar)
            normalized = source.read_text(encoding="utf-8")
            self.assertIn("field.get(clazz)", normalized)
            self.assertIn("clazz.getSimpleName()", normalized)
            self.assertNotIn("field.get(obj)", normalized)
            self.assertNotIn("obj.getSimpleName()", normalized)

            action = next(
                row
                for row in report["actions"]
                if row["kind"]
                == "invokedynamic_captured_class_local_alias"
            )
            self.assertEqual(action["capture_source_name"], "clazz")
            self.assertEqual(action["undeclared_capture_alias"], "obj")
            self.assertEqual(
                action["field_lambda_parameter_name"],
                "field",
            )
            self.assertEqual(action["replacement_count"], 2)
            self.assertEqual(
                report["summary"][
                    "invokedynamic_captured_class_local_alias_action_count"
                ],
                1,
            )
            self.assertEqual(
                report["summary"][
                    "invokedynamic_captured_class_local_alias_reference_count"
                ],
                2,
            )

            after = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "after-captured-class-alias"),
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

    def test_invokedynamic_captured_class_local_alias_requires_capture(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "p/D.java": (
                        "package p;\n"
                        "public class D {\n"
                        "    public D(String value) {}\n"
                        "}\n"
                    ),
                    "p/A.java": (
                        "package p;\n"
                        "import java.util.Arrays;\n"
                        "import java.util.List;\n"
                        "import java.util.stream.Collectors;\n"
                        "public class A {\n"
                        "    public List<D> scan(Object value) {\n"
                        "        Class<?> clazz = value.getClass();\n"
                        "        return Arrays.stream(clazz.getDeclaredFields())\n"
                        "            .map(field -> {\n"
                        "                try {\n"
                        "                    return new D(String.valueOf("
                        "field.get(null)));\n"
                        "                } catch (IllegalAccessException ex) {\n"
                        "                    System.err.println(field.getName());\n"
                        "                    return null;\n"
                        "                }\n"
                        "            })\n"
                        "            .collect(Collectors.toList());\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            original = (
                "package p;\n"
                "import java.util.Arrays;\n"
                "import java.util.List;\n"
                "import java.util.stream.Collectors;\n"
                "public class A {\n"
                "    public List<D> scan(Object value) {\n"
                "        Class<?> clazz = value.getClass();\n"
                "        return Arrays.stream(clazz.getDeclaredFields())\n"
                "            .map(field -> {\n"
                "                try {\n"
                "                    return new D(String.valueOf("
                "field.get(obj)));\n"
                "                } catch (IllegalAccessException ex) {\n"
                "                    System.err.println("
                "obj.getSimpleName() + field.getName());\n"
                "                    return null;\n"
                "                }\n"
                "            })\n"
                "            .collect(Collectors.toList());\n"
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
                    "invokedynamic_captured_class_local_alias_action_count"
                ],
                0,
            )
            self.assertEqual(
                report["summary"][
                    "invokedynamic_captured_class_local_alias_reference_count"
                ],
                0,
            )

    def test_invokedynamic_captured_class_local_alias_requires_declared_class_source(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "p/D.java": (
                        "package p;\n"
                        "public class D {\n"
                        "    public D(String value) {}\n"
                        "}\n"
                    ),
                    "p/A.java": (
                        "package p;\n"
                        "import java.util.Arrays;\n"
                        "import java.util.List;\n"
                        "import java.util.stream.Collectors;\n"
                        "public class A {\n"
                        "    public List<D> scan(Object value) {\n"
                        "        Class<?> clazz = value.getClass();\n"
                        "        return Arrays.stream(clazz.getDeclaredFields())\n"
                        "            .map(field -> {\n"
                        "                try {\n"
                        "                    return new D(String.valueOf("
                        "field.get(clazz)));\n"
                        "                } catch (IllegalAccessException ex) {\n"
                        "                    System.err.println("
                        "clazz.getSimpleName() + field.getName());\n"
                        "                    return null;\n"
                        "                }\n"
                        "            })\n"
                        "            .collect(Collectors.toList());\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            original = (
                "package p;\n"
                "import java.util.Arrays;\n"
                "import java.util.List;\n"
                "import java.util.stream.Collectors;\n"
                "public class A {\n"
                "    public List<D> scan(Object value) {\n"
                "        return Arrays.stream(clazz.getDeclaredFields())\n"
                "            .map(field -> {\n"
                "                try {\n"
                "                    return new D(String.valueOf("
                "field.get(obj)));\n"
                "                } catch (IllegalAccessException ex) {\n"
                "                    System.err.println("
                "obj.getSimpleName() + field.getName());\n"
                "                    return null;\n"
                "                }\n"
                "            })\n"
                "            .collect(Collectors.toList());\n"
                "    }\n"
                "}\n"
            )
            source.write_text(original, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)

            self.assertEqual(source.read_text(encoding="utf-8"), original)
            self.assertEqual(
                report["summary"][
                    "invokedynamic_captured_class_local_alias_action_count"
                ],
                0,
            )
            self.assertEqual(
                report["summary"][
                    "invokedynamic_captured_class_local_alias_reference_count"
                ],
                0,
            )


    def test_collectors_to_list_wildcard_sink_casts_use_exact_sink_signature(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "p/G.java": (
                        "package p;\n"
                        "public class G {}\n"
                    ),
                    "p/M.java": (
                        "package p;\n"
                        "public class M {}\n"
                    ),
                    "p/H.java": (
                        "package p;\n"
                        "public class H {}\n"
                    ),
                    "p/D.java": (
                        "package p;\n"
                        "import java.util.Collection;\n"
                        "public class D {\n"
                        "    public D(G group, Collection<M> sections, "
                        "Collection<H> items) {}\n"
                        "}\n"
                    ),
                    "p/A.java": (
                        "package p;\n"
                        "import java.util.Arrays;\n"
                        "import java.util.List;\n"
                        "import java.util.stream.Collectors;\n"
                        "public class A {\n"
                        "    public D build(Class<?> clazz) {\n"
                        "        List<M> sections = Arrays.stream(\n"
                        "            clazz.getDeclaredFields())\n"
                        "            .map(field -> new M())\n"
                        "            .collect(Collectors.toList());\n"
                        "        List<H> items = Arrays.stream(\n"
                        "            clazz.getMethods())\n"
                        "            .map(method -> new H())\n"
                        "            .collect(Collectors.toList());\n"
                        "        return new D(new G(), sections, items);\n"
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
                "import java.util.Collection;\n"
                "import java.util.List;\n"
                "import java.util.stream.Collector;\n"
                "import java.util.stream.Collectors;\n"
                "public class A {\n"
                "    public D build(Class<?> clazz) {\n"
                "        return new D(new G(),\n"
                "            (Collection<M>)Arrays.stream("
                "clazz.getDeclaredFields())\n"
                "                .map(field -> new M())\n"
                "                .collect((Collector<? super Object, ?, "
                "List<? super Object>>)Collectors.toList()),\n"
                "            (Collection<H>)Arrays.stream("
                "clazz.getMethods())\n"
                "                .map(method -> new H())\n"
                "                .collect((Collector<? super Object, ?, "
                "List<? super Object>>)Collectors.toList()));\n"
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
                    str(root / "before-wildcard-collector"),
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(before.returncode, 0)

            report = normalize_procyon_source(root / "src", jar)
            normalized = source.read_text(encoding="utf-8")
            self.assertNotIn(
                "Collector<? super Object, ?, List<? super Object>>",
                normalized,
            )
            self.assertEqual(
                normalized.count("Collectors.toList()"),
                2,
            )
            self.assertIn("(Collection<M>)Arrays.stream", normalized)
            self.assertIn("(Collection<H>)Arrays.stream", normalized)

            action = next(
                row
                for row in report["actions"]
                if row["kind"]
                == "collectors_to_list_wildcard_sink_cast_removal"
            )
            self.assertEqual(action["source_element_types"], ["M", "H"])
            self.assertEqual(action["exact_element_owners"], ["p/M", "p/H"])
            self.assertEqual(action["sink_owner"], "p/D")
            self.assertEqual(action["replacement_count"], 2)
            self.assertEqual(
                report["summary"][
                    "collectors_to_list_wildcard_sink_cast_action_count"
                ],
                1,
            )
            self.assertEqual(
                report["summary"][
                    "collectors_to_list_wildcard_sink_cast_reference_count"
                ],
                2,
            )

            after = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "after-wildcard-collector"),
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

    def test_collectors_to_list_wildcard_sink_casts_require_typed_sink(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "p/G.java": (
                        "package p;\n"
                        "public class G {}\n"
                    ),
                    "p/M.java": (
                        "package p;\n"
                        "public class M {}\n"
                    ),
                    "p/H.java": (
                        "package p;\n"
                        "public class H {}\n"
                    ),
                    "p/D.java": (
                        "package p;\n"
                        "import java.util.Collection;\n"
                        "public class D {\n"
                        "    public D(G group, Collection<?> sections, "
                        "Collection<?> items) {}\n"
                        "}\n"
                    ),
                    "p/A.java": (
                        "package p;\n"
                        "import java.util.Arrays;\n"
                        "import java.util.List;\n"
                        "import java.util.stream.Collectors;\n"
                        "public class A {\n"
                        "    public D build(Class<?> clazz) {\n"
                        "        List<M> sections = Arrays.stream(\n"
                        "            clazz.getDeclaredFields())\n"
                        "            .map(field -> new M())\n"
                        "            .collect(Collectors.toList());\n"
                        "        List<H> items = Arrays.stream(\n"
                        "            clazz.getMethods())\n"
                        "            .map(method -> new H())\n"
                        "            .collect(Collectors.toList());\n"
                        "        return new D(new G(), sections, items);\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            original = (
                "package p;\n"
                "import java.util.Arrays;\n"
                "import java.util.Collection;\n"
                "import java.util.List;\n"
                "import java.util.stream.Collector;\n"
                "import java.util.stream.Collectors;\n"
                "public class A {\n"
                "    public D build(Class<?> clazz) {\n"
                "        return new D(new G(),\n"
                "            (Collection<M>)Arrays.stream("
                "clazz.getDeclaredFields())\n"
                "                .map(field -> new M())\n"
                "                .collect((Collector<? super Object, ?, "
                "List<? super Object>>)Collectors.toList()),\n"
                "            (Collection<H>)Arrays.stream("
                "clazz.getMethods())\n"
                "                .map(method -> new H())\n"
                "                .collect((Collector<? super Object, ?, "
                "List<? super Object>>)Collectors.toList()));\n"
                "    }\n"
                "}\n"
            )
            source.write_text(original, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)

            self.assertEqual(source.read_text(encoding="utf-8"), original)
            self.assertEqual(
                report["summary"][
                    "collectors_to_list_wildcard_sink_cast_action_count"
                ],
                0,
            )
            self.assertEqual(
                report["summary"][
                    "collectors_to_list_wildcard_sink_cast_reference_count"
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

    def test_enum_valueof_object_class_cast_uses_exact_enum_flow(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "p/A.java": (
                        "package p;\n"
                        "import java.lang.reflect.Type;\n"
                        "public class A {\n"
                        "    public Object parse(String value, Type type) {\n"
                        "        if (type instanceof Class"
                        " && ((Class<?>)type).isEnum()) {\n"
                        "            return Enum.valueOf((Class)type, value);\n"
                        "        }\n"
                        "        return null;\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package p;\n"
                "import java.lang.reflect.Type;\n"
                "public class A {\n"
                "    public Object parse(String value, Type type) {\n"
                "        if (type instanceof Class"
                " && ((Class<?>)type).isEnum()) {\n"
                "            return Enum.valueOf("
                "(Class<Object>)type, value);\n"
                "        }\n"
                "        return null;\n"
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
                    str(root / "before-enum-valueof"),
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
                "Enum.valueOf((Class)type, value)",
                normalized,
            )
            self.assertNotIn("Class<Object>", normalized)

            action = next(
                row
                for row in report["actions"]
                if row["kind"]
                == "enum_valueof_raw_class_cast_reconstruction"
            )
            self.assertEqual(action["class_argument_name"], "type")
            self.assertEqual(action["string_argument_name"], "value")
            self.assertEqual(action["replacement_count"], 1)
            self.assertEqual(
                report["summary"][
                    "enum_valueof_raw_class_cast_action_count"
                ],
                1,
            )
            self.assertEqual(
                report["summary"][
                    "enum_valueof_raw_class_cast_reference_count"
                ],
                1,
            )

            after = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "after-enum-valueof"),
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

    def test_enum_valueof_object_class_cast_requires_is_enum_flow(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "p/A.java": (
                        "package p;\n"
                        "import java.lang.reflect.Type;\n"
                        "public class A {\n"
                        "    public Object parse(String value, Type type) {\n"
                        "        if (type instanceof Class) {\n"
                        "            return Enum.valueOf((Class)type, value);\n"
                        "        }\n"
                        "        return null;\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            original = (
                "package p;\n"
                "import java.lang.reflect.Type;\n"
                "public class A {\n"
                "    public Object parse(String value, Type type) {\n"
                "        if (type instanceof Class"
                " && ((Class<?>)type).isEnum()) {\n"
                "            return Enum.valueOf("
                "(Class<Object>)type, value);\n"
                "        }\n"
                "        return null;\n"
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
                    "enum_valueof_raw_class_cast_action_count"
                ],
                0,
            )
            self.assertEqual(
                report["summary"][
                    "enum_valueof_raw_class_cast_reference_count"
                ],
                0,
            )

    def test_enum_valueof_object_class_cast_rejects_multiple_source_calls(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "p/A.java": (
                        "package p;\n"
                        "import java.lang.reflect.Type;\n"
                        "public class A {\n"
                        "    public Object parse(String value, Type type) {\n"
                        "        if (type instanceof Class"
                        " && ((Class<?>)type).isEnum()) {\n"
                        "            return Enum.valueOf((Class)type, value);\n"
                        "        }\n"
                        "        return null;\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            original = (
                "package p;\n"
                "import java.lang.reflect.Type;\n"
                "public class A {\n"
                "    public Object parse(String value, Type type) {\n"
                "        if (type instanceof Class"
                " && ((Class<?>)type).isEnum()) {\n"
                "            if (value.isEmpty()) {\n"
                "                return Enum.valueOf("
                "(Class<Object>)type, value);\n"
                "            }\n"
                "            return Enum.valueOf("
                "(Class<Object>)type, value);\n"
                "        }\n"
                "        return null;\n"
                "    }\n"
                "}\n"
            )
            source.write_text(original, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)

            self.assertEqual(source.read_text(encoding="utf-8"), original)
            self.assertEqual(
                report["summary"][
                    "enum_valueof_raw_class_cast_action_count"
                ],
                0,
            )
            self.assertEqual(
                report["summary"][
                    "enum_valueof_raw_class_cast_reference_count"
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
                8,
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

    def test_same_package_static_method_owner_inherited_api_shadowed_by_field(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "p/Base.java": (
                        "package p;\n"
                        "public class Base {\n"
                        "    public static boolean a() { return true; }\n"
                        "    public static void a(boolean value) {}\n"
                        "}\n"
                    ),
                    "p/c.java": (
                        "package p;\n"
                        "public class c extends Base {}\n"
                    ),
                    "p/h.java": (
                        "package p;\n"
                        "public class h {\n"
                        "    public int c;\n"
                        "    public static void m() {\n"
                        "        boolean value = p.c.a();\n"
                        "        p.c.a(value);\n"
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
                "    public int c;\n"
                "    public static void m() {\n"
                "        boolean value = c.a();\n"
                "        c.a(value);\n"
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
                    str(root / "before-inherited-same-package-call"),
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(before.returncode, 0)
            self.assertIn("non-static variable c", before.stderr)

            report = normalize_procyon_source(root / "src", jar)
            normalized = source.read_text(encoding="utf-8")

            self.assertIn("boolean value = p.c.a();", normalized)
            self.assertIn("p.c.a(value);", normalized)
            action = next(
                row
                for row in report["actions"]
                if row["kind"]
                == "shadowed_same_package_static_method_owner_qualification"
            )
            self.assertEqual(action["same_package_owner"], "p/c")
            self.assertEqual(action["hierarchy_shadow_owner"], "p/h")
            self.assertEqual(action["call_counts"], {"a": 2})
            self.assertEqual(action["replacement_count"], 2)

            after = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "after-inherited-same-package-call"),
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

    def test_same_package_static_method_owner_matches_source_staticness(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "p/c.java": (
                        "package p;\n"
                        "public class c {\n"
                        "    public static int a() { return 7; }\n"
                        "}\n"
                    ),
                    "p1/Ref.java": (
                        "package p1;\n"
                        "public class Ref {}\n"
                    ),
                    "p2/Ref.java": (
                        "package p2;\n"
                        "public class Ref {}\n"
                    ),
                    "p/h.java": (
                        "package p;\n"
                        "public class h {\n"
                        "    public int c;\n"
                        "    public static int m(p1.Ref ref) {\n"
                        "        return p.c.a();\n"
                        "    }\n"
                        "    public int m(p2.Ref ref) {\n"
                        "        return p.c.a();\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )
            source = root / "src" / "p" / "h.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package p;\n"
                "import p1.Ref;\n"
                "public class h {\n"
                "    public int c;\n"
                "    public static int m(final Ref ref) {\n"
                "        return c.a();\n"
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
                    str(root / "before-same-package-call-staticness"),
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(before.returncode, 0)

            report = normalize_procyon_source(root / "src", jar)
            normalized = source.read_text(encoding="utf-8")

            self.assertIn("return p.c.a();", normalized)
            action = next(
                row
                for row in report["actions"]
                if row["kind"]
                == "shadowed_same_package_static_method_owner_qualification"
            )
            self.assertEqual(action["method_name"], "m")
            self.assertEqual(action["method_descriptor"], "(Lp1/Ref;)I")
            self.assertEqual(action["same_package_owner"], "p/c")
            self.assertEqual(action["replacement_count"], 1)

            after = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "after-same-package-call-staticness"),
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





class LinkedHashMapFieldGetResultCastTests(unittest.TestCase):
    def _fixture(
        self,
        root: Path,
        *,
        map_super: str = "LinkedHashMap<String, ItemList>",
        duplicate_exact: bool = False,
    ) -> Path:
        exact_get = (
            '((LinkedHashMap)folders).get'
            if map_super.startswith("LinkedHashMap<")
            else '(Object)folders.get'
        )
        second = (
            '        store.save("Other", (List<Item>)'
            + exact_get
            + '("Other"));\n'
            if duplicate_exact
            else ""
        )
        return _compile_java_fixture(
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
                "p/FolderMap.java": (
                    "package p;\n"
                    "import java.util.LinkedHashMap;\n"
                    "import java.util.HashMap;\n"
                    f"public class FolderMap extends {map_super} {{}}\n"
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
                    "public class A {\n"
                    "    private final FolderMap folders = new FolderMap();\n"
                    "    private final Store store = new Store();\n"
                    "    public A() {\n"
                    '        store.save("Main folder", (List<Item>)'
                    + exact_get
                    + '("Main folder"));\n'
                    + second
                    + "    }\n"
                    "}\n"
                ),
            },
        )

    def _malformed_source(self, *, duplicate_source: bool = False) -> str:
        second = (
            '        store.save("Other", '
            '((LinkedHashMap<K, List<Item>>)this.folders).get("Other"));\n'
            if duplicate_source
            else ""
        )
        return (
            "package p;\n"
            "import java.util.LinkedHashMap;\n"
            "import java.util.List;\n"
            "public class A {\n"
            "    private final FolderMap folders = new FolderMap();\n"
            "    private final Store store = new Store();\n"
            "    public A() {\n"
            '        store.save("Main folder", '
            '((LinkedHashMap<K, List<Item>>)this.folders)'
            '.get("Main folder"));\n'
            + second
            + "    }\n"
            "}\n"
        )

    def test_constructor_field_get_moves_impossible_receiver_cast_to_result(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._fixture(root)
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                self._malformed_source(),
                encoding="utf-8",
            )

            before = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "before-map-field-result"),
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
                'store.save("Main folder", '
                '((List<Item>)((LinkedHashMap)this.folders)'
                '.get("Main folder")));',
                normalized,
            )
            self.assertNotIn("LinkedHashMap<K, List<Item>>", normalized)

            actions = [
                row
                for row in report["actions"]
                if row["kind"] == "linkedhashmap_field_get_result_cast"
            ]
            self.assertEqual(len(actions), 1)
            action = actions[0]
            self.assertEqual(action["method_name"], "<init>")
            self.assertEqual(action["method_descriptor"], "()V")
            self.assertEqual(action["field_names"], ["folders"])
            self.assertEqual(action["field_owners"], ["p/FolderMap"])
            self.assertEqual(
                action["field_signatures"],
                [
                    "Ljava/util/LinkedHashMap<"
                    "Ljava/lang/String;Lp/ItemList;>;"
                ],
            )
            self.assertEqual(action["result_types"], ["List<Item>"])
            self.assertEqual(action["replacement_count"], 1)
            self.assertEqual(len(action["exact_flows"]), 1)
            self.assertEqual(
                report["summary"][
                    "linkedhashmap_field_get_result_cast_action_count"
                ],
                1,
            )
            self.assertEqual(
                report["summary"][
                    "linkedhashmap_field_get_result_cast_reference_count"
                ],
                1,
            )

            after = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "after-map-field-result"),
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(after.returncode, 0, after.stdout + after.stderr)

    def test_constructor_field_get_requires_direct_linkedhashmap_signature(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._fixture(
                root,
                map_super="HashMap<String, ItemList>",
            )
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            original = self._malformed_source()
            source.write_text(original, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)

            self.assertEqual(source.read_text(encoding="utf-8"), original)
            self.assertEqual(
                report["summary"][
                    "linkedhashmap_field_get_result_cast_reference_count"
                ],
                0,
            )

    def test_constructor_field_get_fails_closed_on_multiplicity_drift(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._fixture(root)
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            original = self._malformed_source(duplicate_source=True)
            source.write_text(original, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)

            self.assertEqual(source.read_text(encoding="utf-8"), original)
            self.assertEqual(
                report["summary"][
                    "linkedhashmap_field_get_result_cast_reference_count"
                ],
                0,
            )



class ErasedHashMapArrayReturnCastTests(unittest.TestCase):
    def _fixture(
        self,
        root: Path,
        *,
        return_type: str = "int[]",
    ) -> Path:
        literal = {
            "int[]": "new int[] {1}",
            "boolean[]": "new boolean[] {true}",
        }[return_type]
        return _compile_java_fixture(
            root,
            {
                "p/Key.java": (
                    "package p;\n"
                    "public class Key {}\n"
                ),
                "p/A.java": (
                    "package p;\n"
                    "import java.util.HashMap;\n"
                    "public class A {\n"
                    "    public HashMap<Key, Object> f = new HashMap<>();\n"
                    f"    public {return_type} read(Key key) {{\n"
                    f"        f.put(key, {literal});\n"
                    f"        return ({return_type})this.f.get(key);\n"
                    "    }\n"
                    "}\n"
                ),
            },
        )

    def test_hashmap_object_value_array_return_restores_exact_cast(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._fixture(root)
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package p;\n"
                "import java.util.HashMap;\n"
                "public class A {\n"
                "    public HashMap<Key, Object> f = new HashMap<>();\n"
                "    public int[] read(Key key) {\n"
                "        return this.f.get(key);\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )

            before = subprocess.run(
                [
                    "javac", "-cp", str(jar), "-d",
                    str(root / "before-hashmap-array"), str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(before.returncode, 0)

            report = normalize_procyon_source(root / "src", jar)
            normalized = source.read_text(encoding="utf-8")
            self.assertIn(
                "return (int[])this.f.get(key);",
                normalized,
            )
            action = next(
                row
                for row in report["actions"]
                if row["kind"]
                == "erased_hashmap_get_array_return_cast_reconstruction"
            )
            self.assertEqual(action["array_return_descriptor"], "[I")
            self.assertEqual(action["field_names"], ["f"])
            self.assertEqual(action["replacement_count"], 1)

            after = subprocess.run(
                [
                    "javac", "-cp", str(jar), "-d",
                    str(root / "after-hashmap-array"), str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(after.returncode, 0, after.stderr)

    def test_hashmap_object_value_array_return_fails_closed_on_type_drift(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._fixture(root, return_type="boolean[]")
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            malformed = (
                "package p;\n"
                "import java.util.HashMap;\n"
                "public class A {\n"
                "    public HashMap<Key, Object> f = new HashMap<>();\n"
                "    public int[] read(Key key) {\n"
                "        return this.f.get(key);\n"
                "    }\n"
                "}\n"
            )
            source.write_text(malformed, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)
            self.assertEqual(source.read_text(encoding="utf-8"), malformed)
            self.assertFalse(
                any(
                    row["kind"]
                    == "erased_hashmap_get_array_return_cast_reconstruction"
                    for row in report["actions"]
                )
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

    def test_erased_map_number_assignment_restores_elided_terminal_cast(
        self,
    ):
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
                "        return value.intValue();\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )

            before = subprocess.run(
                ["javac", "-d", str(root / "before-map-elided"), str(source)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(before.returncode, 0)

            report = normalize_procyon_source(root / "src", jar)
            normalized = source.read_text(encoding="utf-8")
            self.assertIn("final Object value = map.get(s);", normalized)
            self.assertIn(
                "return ((Number)value).intValue();",
                normalized,
            )
            action = next(
                row
                for row in report["actions"]
                if row["kind"]
                == "erased_map_number_assignment_reconstruction"
            )
            self.assertEqual(action["replacement_count"], 1)
            self.assertEqual(action["terminal_cast_replacement_count"], 1)

            after = subprocess.run(
                ["javac", "-d", str(root / "after-map-elided"), str(source)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(after.returncode, 0, after.stderr)

    def test_erased_map_number_assignment_rejects_multiple_plain_terminals(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._fixture(root)
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
                "        return value.intValue() + value.intValue();\n"
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




class ErasedRawCollectionGetAssignmentTests(unittest.TestCase):
    def _fixture(self, root: Path) -> Path:
        return _compile_java_fixture(
            root,
            {
                "p/A.java": (
                    "package p;\n"
                    "import java.util.List;\n"
                    "import java.util.Map;\n"
                    "public class A {\n"
                    "    public static String mapValue("
                    "Map map, Object key) {\n"
                    "        String value = (String)map.get(key);\n"
                    "        return value;\n"
                    "    }\n"
                    "    public static List listValue("
                    "List list, int i) {\n"
                    "        List value = (List)list.get(i);\n"
                    "        return value;\n"
                    "    }\n"
                    "}\n"
                )
            },
        )

    def test_raw_map_and_list_get_assignments_restore_exact_casts(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._fixture(root)
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package p;\n"
                "import java.util.List;\n"
                "import java.util.Map;\n"
                "public class A {\n"
                "    public static String mapValue("
                "Map map, Object key) {\n"
                "        final String value = map.get(key);\n"
                "        return value;\n"
                "    }\n"
                "    public static List listValue("
                "List list, int i) {\n"
                "        final List value = list.get(i);\n"
                "        return value;\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )

            before = subprocess.run(
                [
                    "javac", "-cp", str(jar), "-d",
                    str(root / "before-raw-get"), str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(before.returncode, 0)

            report = normalize_procyon_source(root / "src", jar)
            normalized = source.read_text(encoding="utf-8")
            self.assertIn(
                "final String value = (String)map.get(key);",
                normalized,
            )
            self.assertIn(
                "final List value = (List)list.get(i);",
                normalized,
            )
            actions = [
                row
                for row in report["actions"]
                if row["kind"]
                == "erased_raw_collection_get_assignment_cast_reconstruction"
            ]
            self.assertEqual(len(actions), 2)
            self.assertEqual(
                sorted(
                    cast
                    for row in actions
                    for cast in row["exact_checkcast_types"]
                ),
                ["java/lang/String", "java/util/List"],
            )
            self.assertEqual(
                report["summary"][
                    "erased_raw_collection_get_assignment_cast_action_count"
                ],
                2,
            )
            self.assertEqual(
                report["summary"][
                    "erased_raw_collection_get_assignment_cast_reference_count"
                ],
                2,
            )

            after = subprocess.run(
                [
                    "javac", "-cp", str(jar), "-d",
                    str(root / "after-raw-get"), str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(after.returncode, 0, after.stderr)

    def test_raw_collection_get_assignment_fails_closed_on_cast_drift(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "p/A.java": (
                        "package p;\n"
                        "import java.util.Map;\n"
                        "public class A {\n"
                        "    public static String mapValue("
                        "Map map, Object key) {\n"
                        "        Integer value = (Integer)map.get(key);\n"
                        "        return String.valueOf(value);\n"
                        "    }\n"
                        "}\n"
                    )
                },
            )
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            malformed = (
                "package p;\n"
                "import java.util.Map;\n"
                "public class A {\n"
                "    public static String mapValue("
                "Map map, Object key) {\n"
                "        final String value = map.get(key);\n"
                "        return value;\n"
                "    }\n"
                "}\n"
            )
            source.write_text(malformed, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)
            self.assertEqual(source.read_text(encoding="utf-8"), malformed)
            self.assertFalse(
                any(
                    row["kind"]
                    == "erased_raw_collection_get_assignment_cast_reconstruction"
                    for row in report["actions"]
                )
            )


class ErasedRawListToArrayReturnTests(unittest.TestCase):
    def _fixture(self, root: Path) -> Path:
        return _compile_java_fixture(
            root,
            {
                "p/A.java": (
                    "package p;\n"
                    "import java.util.List;\n"
                    "public class A {\n"
                    "    public static String[] values(Object o) {\n"
                    "        return (String[])((List)o).toArray("
                    "new String[((List)o).size()]);\n"
                    "    }\n"
                    "}\n"
                )
            },
        )

    def test_raw_list_toarray_return_restores_exact_array_cast(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._fixture(root)
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package p;\n"
                "import java.util.List;\n"
                "public class A {\n"
                "    public static String[] values(Object o) {\n"
                "        return ((List)o).toArray("
                "new String[((List)o).size()]);\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )

            before = subprocess.run(
                [
                    "javac", "-cp", str(jar), "-d",
                    str(root / "before-list-toarray"), str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(before.returncode, 0)

            report = normalize_procyon_source(root / "src", jar)
            normalized = source.read_text(encoding="utf-8")
            self.assertIn(
                "return (String[])((List)o).toArray("
                "new String[((List)o).size()]);",
                normalized,
            )
            action = next(
                row
                for row in report["actions"]
                if row["kind"]
                == "erased_raw_list_toarray_return_cast_reconstruction"
            )
            self.assertEqual(action["array_return_descriptor"], "[Ljava/lang/String;")
            self.assertEqual(action["component_types"], ["String"])
            self.assertEqual(action["replacement_count"], 1)
            self.assertEqual(
                report["summary"][
                    "erased_raw_list_toarray_return_cast_reference_count"
                ],
                1,
            )

            after = subprocess.run(
                [
                    "javac", "-cp", str(jar), "-d",
                    str(root / "after-list-toarray"), str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(after.returncode, 0, after.stderr)

    def test_raw_list_toarray_return_fails_closed_on_component_drift(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._fixture(root)
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            malformed = (
                "package p;\n"
                "import java.util.List;\n"
                "public class A {\n"
                "    public static String[] values(Object o) {\n"
                "        return ((List)o).toArray("
                "new Integer[((List)o).size()]);\n"
                "    }\n"
                "}\n"
            )
            source.write_text(malformed, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)
            self.assertEqual(source.read_text(encoding="utf-8"), malformed)
            self.assertFalse(
                any(
                    row["kind"]
                    == "erased_raw_list_toarray_return_cast_reconstruction"
                    for row in report["actions"]
                )
            )


class ErasedNestedListReceiverTests(unittest.TestCase):
    def _fixture(self, root: Path) -> Path:
        return _compile_java_fixture(
            root,
            {
                "p/A.java": (
                    "package p;\n"
                    "import java.util.List;\n"
                    "public class A {\n"
                    "    public static int sizeAt(List list, int i) {\n"
                    "        return ((List)list.get(i)).size();\n"
                    "    }\n"
                    "    public static Object valueAt("
                    "List list, int i, int j) {\n"
                    "        return ((List)list.get(i)).get(j);\n"
                    "    }\n"
                    "}\n"
                )
            },
        )

    def test_nested_raw_list_receivers_restore_exact_list_casts(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._fixture(root)
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package p;\n"
                "import java.util.List;\n"
                "public class A {\n"
                "    public static int sizeAt(List list, int i) {\n"
                "        return list.get(i).size();\n"
                "    }\n"
                "    public static Object valueAt("
                "List list, int i, int j) {\n"
                "        return list.get(i).get(j);\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )

            before = subprocess.run(
                [
                    "javac", "-cp", str(jar), "-d",
                    str(root / "before-nested-list"), str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(before.returncode, 0)

            report = normalize_procyon_source(root / "src", jar)
            normalized = source.read_text(encoding="utf-8")
            self.assertIn(
                "return ((List)list.get(i)).size();",
                normalized,
            )
            self.assertIn(
                "return ((List)list.get(i)).get(j);",
                normalized,
            )
            actions = [
                row
                for row in report["actions"]
                if row["kind"]
                == "erased_nested_list_receiver_cast_reconstruction"
            ]
            self.assertEqual(len(actions), 2)
            self.assertEqual(
                sorted(
                    (
                        row["member_counts"]["get"],
                        row["member_counts"]["size"],
                    )
                    for row in actions
                ),
                [(0, 1), (1, 0)],
            )
            self.assertEqual(
                report["summary"][
                    "erased_nested_list_receiver_cast_reference_count"
                ],
                2,
            )

            after = subprocess.run(
                [
                    "javac", "-cp", str(jar), "-d",
                    str(root / "after-nested-list"), str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(after.returncode, 0, after.stderr)

    def test_nested_raw_list_receiver_fails_closed_on_cast_drift(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "p/A.java": (
                        "package p;\n"
                        "import java.util.ArrayList;\n"
                        "import java.util.List;\n"
                        "public class A {\n"
                        "    public static int sizeAt(List list, int i) {\n"
                        "        return ((ArrayList)list.get(i)).size();\n"
                        "    }\n"
                        "}\n"
                    )
                },
            )
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            malformed = (
                "package p;\n"
                "import java.util.List;\n"
                "public class A {\n"
                "    public static int sizeAt(List list, int i) {\n"
                "        return list.get(i).size();\n"
                "    }\n"
                "}\n"
            )
            source.write_text(malformed, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)
            self.assertEqual(source.read_text(encoding="utf-8"), malformed)
            self.assertFalse(
                any(
                    row["kind"]
                    == "erased_nested_list_receiver_cast_reconstruction"
                    for row in report["actions"]
                )
            )


class ErasedNestedListIntegerUnboxTests(unittest.TestCase):
    def _fixture(self, root: Path) -> Path:
        return _compile_java_fixture(
            root,
            {
                "p/A.java": (
                    "package p;\n"
                    "import java.util.List;\n"
                    "public class A {\n"
                    "    public static int valueAt("
                    "List list, int i, int j) {\n"
                    "        return ((Integer)((List)list.get(i)).get(j))"
                    ".intValue();\n"
                    "    }\n"
                    "}\n"
                )
            },
        )

    def test_nested_raw_list_integer_flow_restores_cast_and_unbox(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._fixture(root)
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package p;\n"
                "import java.util.List;\n"
                "public class A {\n"
                "    public static int valueAt("
                "List list, int i, int j) {\n"
                "        return list.get(i).get(j);\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )

            before = subprocess.run(
                [
                    "javac", "-cp", str(jar), "-d",
                    str(root / "before-nested-int"), str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(before.returncode, 0)

            report = normalize_procyon_source(root / "src", jar)
            normalized = source.read_text(encoding="utf-8")
            self.assertIn(
                "return ((Integer)((List)list.get(i)).get(j)).intValue();",
                normalized,
            )
            action = next(
                row
                for row in report["actions"]
                if row["kind"]
                == "erased_nested_list_integer_unbox_reconstruction"
            )
            self.assertEqual(action["replacement_count"], 1)
            self.assertEqual(len(action["exact_list_checkcast_offsets"]), 1)
            self.assertEqual(
                len(action["exact_integer_checkcast_offsets"]),
                1,
            )
            self.assertEqual(
                report["summary"][
                    "erased_nested_list_integer_unbox_reference_count"
                ],
                1,
            )

            after = subprocess.run(
                [
                    "javac", "-cp", str(jar), "-d",
                    str(root / "after-nested-int"), str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(after.returncode, 0, after.stderr)

    def test_nested_raw_list_integer_flow_fails_closed_on_type_drift(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "p/A.java": (
                        "package p;\n"
                        "import java.util.List;\n"
                        "public class A {\n"
                        "    public static int valueAt("
                        "List list, int i, int j) {\n"
                        "        return ((Long)((List)list.get(i)).get(j))"
                        ".intValue();\n"
                        "    }\n"
                        "}\n"
                    )
                },
            )
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package p;\n"
                "import java.util.List;\n"
                "public class A {\n"
                "    public static int valueAt("
                "List list, int i, int j) {\n"
                "        return list.get(i).get(j);\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )

            report = normalize_procyon_source(root / "src", jar)
            normalized = source.read_text(encoding="utf-8")
            self.assertIn(
                "return ((List)list.get(i)).get(j);",
                normalized,
            )
            self.assertFalse(
                any(
                    row["kind"]
                    == "erased_nested_list_integer_unbox_reconstruction"
                    for row in report["actions"]
                )
            )




class ErasedRawListIntegerStreamMethodRefTests(unittest.TestCase):
    def _fixture(
        self,
        root: Path,
        *,
        element_type: str = "Integer",
    ) -> Path:
        return _compile_java_fixture(
            root,
            {
                "p/A.java": (
                    "package p;\n"
                    "import java.util.List;\n"
                    "public class A {\n"
                    "    public static int[] values(Object o) {\n"
                    f"        return ((List<{element_type}>)o).stream()"
                    f".mapToInt({element_type}::intValue).toArray();\n"
                    "    }\n"
                    "}\n"
                )
            },
        )

    def test_raw_list_integer_stream_restores_generic_cast(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._fixture(root)
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package p;\n"
                "import java.util.List;\n"
                "public class A {\n"
                "    public static int[] values(Object o) {\n"
                "        return ((List)o).stream()"
                ".mapToInt(Integer::intValue).toArray();\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )

            before = subprocess.run(
                [
                    "javac", "-cp", str(jar), "-d",
                    str(root / "before-int-stream"), str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(before.returncode, 0)

            report = normalize_procyon_source(root / "src", jar)
            normalized = source.read_text(encoding="utf-8")
            self.assertIn(
                "return ((List<Integer>)o).stream()"
                ".mapToInt(Integer::intValue).toArray();",
                normalized,
            )
            action = next(
                row
                for row in report["actions"]
                if row["kind"]
                == "erased_raw_list_integer_stream_method_ref_reconstruction"
            )
            self.assertEqual(action["element_type"], "java/lang/Integer")
            self.assertEqual(action["replacement_count"], 1)
            self.assertEqual(len(action["flows"]), 1)
            self.assertEqual(
                report["summary"][
                    "erased_raw_list_integer_stream_method_ref_reference_count"
                ],
                1,
            )

            after = subprocess.run(
                [
                    "javac", "-cp", str(jar), "-d",
                    str(root / "after-int-stream"), str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(after.returncode, 0, after.stderr)

    def test_raw_list_integer_stream_fails_closed_on_element_drift(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._fixture(root, element_type="Long")
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            malformed = (
                "package p;\n"
                "import java.util.List;\n"
                "public class A {\n"
                "    public static int[] values(Object o) {\n"
                "        return ((List)o).stream()"
                ".mapToInt(Integer::intValue).toArray();\n"
                "    }\n"
                "}\n"
            )
            source.write_text(malformed, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)
            self.assertEqual(source.read_text(encoding="utf-8"), malformed)
            self.assertFalse(
                any(
                    row["kind"]
                    == "erased_raw_list_integer_stream_method_ref_reconstruction"
                    for row in report["actions"]
                )
            )




class ErasedMapGetDirectArgumentCastTests(unittest.TestCase):
    def _fixture(
        self,
        root: Path,
        *,
        target_type: str = "Map",
    ) -> Path:
        import_line = (
            "import java.util.Map;\n"
            if target_type == "Map"
            else "import java.util.List;\nimport java.util.Map;\n"
        )
        return _compile_java_fixture(
            root,
            {
                "p/A.java": (
                    "package p;\n"
                    + import_line
                    + "import java.util.HashMap;\n"
                    "public class A {\n"
                    f"    public Object decode(int key, {target_type} value) {{\n"
                    "        return value;\n"
                    "    }\n"
                    "    public Object read(int key) {\n"
                    "        Map values = new HashMap();\n"
                    f"        return this.decode(key, ({target_type})"
                    "values.get(key));\n"
                    "    }\n"
                    "}\n"
                )
            },
        )

    def test_map_get_direct_argument_restores_exact_cast(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._fixture(root)
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package p;\n"
                "import java.util.HashMap;\n"
                "import java.util.Map;\n"
                "public class A {\n"
                "    public Object decode(int key, Map value) {\n"
                "        return value;\n"
                "    }\n"
                "    public Object read(int key) {\n"
                "        Map values = new HashMap();\n"
                "        return this.decode(key, values.get(key));\n"
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
                    str(root / "before-map-argument"),
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
                "return this.decode(key, "
                "(java.util.Map)values.get(key));",
                normalized,
            )
            action = next(
                row
                for row in report["actions"]
                if row["kind"]
                == "erased_map_get_direct_argument_cast_reconstruction"
            )
            self.assertEqual(action["target_methods"], ["decode"])
            self.assertEqual(action["receiver_names"], ["values"])
            self.assertEqual(action["replacement_count"], 1)
            self.assertEqual(len(action["flows"]), 1)
            self.assertEqual(
                action["flows"][0]["target_descriptor"],
                "(ILjava/util/Map;)Ljava/lang/Object;",
            )
            self.assertEqual(
                report["summary"][
                    "erased_map_get_direct_argument_cast_reference_count"
                ],
                1,
            )

            after = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "after-map-argument"),
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(after.returncode, 0, after.stderr)

    def test_map_get_direct_argument_fails_closed_on_cast_drift(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._fixture(root, target_type="List")
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            malformed = (
                "package p;\n"
                "import java.util.HashMap;\n"
                "import java.util.List;\n"
                "import java.util.Map;\n"
                "public class A {\n"
                "    public Object decode(int key, List value) {\n"
                "        return value;\n"
                "    }\n"
                "    public Object read(int key) {\n"
                "        Map values = new HashMap();\n"
                "        return this.decode(key, values.get(key));\n"
                "    }\n"
                "}\n"
            )
            source.write_text(malformed, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)
            self.assertEqual(source.read_text(encoding="utf-8"), malformed)
            self.assertFalse(
                any(
                    row["kind"]
                    == "erased_map_get_direct_argument_cast_reconstruction"
                    for row in report["actions"]
                )
            )


class ErasedRawMapStringKeyStreamPredicateTests(unittest.TestCase):
    def _fixture(
        self,
        root: Path,
        *,
        helper_method: str = "equalsIgnoreCase",
    ) -> Path:
        return _compile_java_fixture(
            root,
            {
                "p/A.java": (
                    "package p;\n"
                    "import java.util.HashMap;\n"
                    "import java.util.Map;\n"
                    "public class A {\n"
                    "    public static boolean read() {\n"
                    "        Map map = new HashMap();\n"
                    "        return ((java.util.Set<String>)map.keySet())"
                    ".stream().anyMatch(s -> s."
                    + helper_method
                    + "(\"forceAllRevisions\"));\n"
                    "    }\n"
                    "}\n"
                )
            },
        )

    def test_raw_map_string_key_stream_restores_type_context(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._fixture(root)
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package p;\n"
                "import java.util.HashMap;\n"
                "import java.util.Map;\n"
                "public class A {\n"
                "    public static boolean read() {\n"
                "        Map map = new HashMap();\n"
                "        return map.keySet().stream().anyMatch("
                "s -> s.equalsIgnoreCase(\"forceAllRevisions\"));\n"
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
                    str(root / "before-map-key-stream"),
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
                "return ((java.util.Set<String>)map.keySet()).stream()"
                ".anyMatch(s -> s.equalsIgnoreCase("
                "\"forceAllRevisions\"));",
                normalized,
            )
            action = next(
                row
                for row in report["actions"]
                if row["kind"]
                == "erased_raw_map_string_key_stream_predicate_reconstruction"
            )
            self.assertEqual(action["receiver_names"], ["map"])
            self.assertEqual(action["literals"], ["forceAllRevisions"])
            self.assertEqual(action["replacement_count"], 1)
            self.assertEqual(len(action["flows"]), 1)
            self.assertEqual(
                report["summary"][
                    "erased_raw_map_string_key_stream_predicate_reference_count"
                ],
                1,
            )

            after = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "after-map-key-stream"),
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(after.returncode, 0, after.stderr)

    def test_raw_map_string_key_stream_fails_closed_on_helper_drift(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._fixture(root, helper_method="startsWith")
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            malformed = (
                "package p;\n"
                "import java.util.HashMap;\n"
                "import java.util.Map;\n"
                "public class A {\n"
                "    public static boolean read() {\n"
                "        Map map = new HashMap();\n"
                "        return map.keySet().stream().anyMatch("
                "s -> s.equalsIgnoreCase(\"forceAllRevisions\"));\n"
                "    }\n"
                "}\n"
            )
            source.write_text(malformed, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)
            self.assertEqual(source.read_text(encoding="utf-8"), malformed)
            self.assertFalse(
                any(
                    row["kind"]
                    == (
                        "erased_raw_map_string_key_stream_predicate_"
                        "reconstruction"
                    )
                    for row in report["actions"]
                )
            )



class RawIterableMapEntryLambdaTests(unittest.TestCase):
    def _fixture(
        self,
        root: Path,
        *,
        getter_drift: bool = False,
        filter_drift: bool = False,
        duplicate: bool = False,
    ) -> Path:
        getter_entry = (
            "Map.Entry<String, V>"
            if getter_drift
            else "Map.Entry<K, V>"
        )
        filters = (
            "package p;\n"
            "import java.util.Map;\n"
            "import java.util.function.Predicate;\n"
            "public final class Filters {\n"
            "    public static Iterable c(\n"
            "            Iterable values,\n"
            "            Predicate<Map.Entry<Class<?>, A.Subscriber>> "
            "predicate) {\n"
            "        return values;\n"
            "    }\n"
            "}\n"
            if filter_drift
            else
            "package p;\n"
            "import java.util.function.Predicate;\n"
            "public final class Filters {\n"
            "    public static <T> Iterable<T> c(\n"
            "            Iterable<T> values,\n"
            "            Predicate<? super T> predicate) {\n"
            "        return values;\n"
            "    }\n"
            "}\n"
        )
        duplicate_call = (
            "        Filters.c(this.subscribers.B(), "
            "entry -> entry.getValue().getObject() == o);\n"
            if duplicate
            else ""
        )
        return _compile_java_fixture(
            root,
            {
                "p/Entries.java": (
                    "package p;\n"
                    "import java.util.Collections;\n"
                    "import java.util.Iterator;\n"
                    "public final class Entries<T> "
                    "implements Iterable<T> {\n"
                    "    public Iterator<T> iterator() {\n"
                    "        return Collections.<T>emptyList().iterator();\n"
                    "    }\n"
                    "}\n"
                ),
                "p/Bag.java": (
                    "package p;\n"
                    "import java.util.Map;\n"
                    "public final class Bag<K, V> {\n"
                    "    public Entries<" + getter_entry + "> B() {\n"
                    "        return new Entries<>();\n"
                    "    }\n"
                    "}\n"
                ),
                "p/Filters.java": filters,
                "p/A.java": (
                    "package p;\n"
                    "public class A {\n"
                    "    public static final class Subscriber {\n"
                    "        private final Object object;\n"
                    "        public Subscriber(Object object) {\n"
                    "            this.object = object;\n"
                    "        }\n"
                    "        public Object getObject() {\n"
                    "            return this.object;\n"
                    "        }\n"
                    "    }\n"
                    "    private Bag<Class<?>, Subscriber> subscribers "
                    "= new Bag<>();\n"
                    "    public void unregister(Object o) {\n"
                    "        Filters.c(this.subscribers.B(), "
                    "entry -> entry.getValue().getObject() != o);\n"
                    + duplicate_call +
                    "    }\n"
                    "    public void unregisterSubscriber("
                    "Subscriber subscriber) {\n"
                    "        Filters.c(this.subscribers.B(), "
                    "entry -> subscriber != entry.getValue());\n"
                    "    }\n"
                    "}\n"
                ),
            },
        )

    def _malformed_source(
        self,
        *,
        include_second: bool = True,
    ) -> str:
        second = (
            "    public void unregisterSubscriber("
            "Subscriber subscriber) {\n"
            "        Filters.c((Iterable)this.subscribers.B(), "
            "entry -> subscriber != entry.getValue());\n"
            "    }\n"
            if include_second
            else ""
        )
        return (
            "package p;\n"
            "public class A {\n"
            "    public static final class Subscriber {\n"
            "        private final Object object;\n"
            "        public Subscriber(Object object) {\n"
            "            this.object = object;\n"
            "        }\n"
            "        public Object getObject() {\n"
            "            return this.object;\n"
            "        }\n"
            "    }\n"
            "    private Bag<Class<?>, Subscriber> subscribers "
            "= new Bag<>();\n"
            "    public void unregister(Object o) {\n"
            "        Filters.c((Iterable)this.subscribers.B(), "
            "entry -> entry.getValue().getObject() != o);\n"
            "    }\n"
            + second +
            "}\n"
        )

    def test_raw_iterable_entry_lambdas_remove_only_erasing_casts(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._fixture(root)
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                self._malformed_source(),
                encoding="utf-8",
            )

            before = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "before-entry-lambda"),
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(before.returncode, 0)

            report = normalize_procyon_source(root / "src", jar)
            normalized = source.read_text(encoding="utf-8")
            self.assertNotIn(
                "(Iterable)this.subscribers.B()",
                normalized,
            )
            self.assertEqual(
                normalized.count("Filters.c(this.subscribers.B(),"),
                2,
            )

            actions = [
                row
                for row in report["actions"]
                if row["kind"]
                == "raw_iterable_map_entry_lambda_cast_removal"
            ]
            self.assertEqual(len(actions), 2)
            self.assertEqual(
                {row["method_name"] for row in actions},
                {"unregister", "unregisterSubscriber"},
            )
            self.assertTrue(
                all(row["replacement_count"] == 1 for row in actions)
            )
            self.assertTrue(
                all(
                    row["functional_owner"]
                    == "java/util/function/Predicate"
                    for row in actions
                )
            )
            self.assertTrue(
                all(
                    len(row["filter_proofs"]) == 1
                    and row["filter_proofs"][0]["type_variable"] == "T"
                    for row in actions
                )
            )
            helper_descriptors = {
                row["lambda_bootstraps"][0]["helper_descriptor"]
                for row in actions
            }
            self.assertIn(
                "(Ljava/lang/Object;Ljava/util/Map$Entry;)Z",
                helper_descriptors,
            )
            self.assertIn(
                "(Lp/A$Subscriber;Ljava/util/Map$Entry;)Z",
                helper_descriptors,
            )
            self.assertEqual(
                report["summary"][
                    "raw_iterable_map_entry_lambda_cast_action_count"
                ],
                2,
            )
            self.assertEqual(
                report["summary"][
                    "raw_iterable_map_entry_lambda_cast_reference_count"
                ],
                2,
            )

            after = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "after-entry-lambda"),
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

    def test_raw_iterable_entry_lambda_fails_on_getter_signature_drift(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._fixture(root, getter_drift=True)
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            malformed = self._malformed_source()
            source.write_text(malformed, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)

            self.assertEqual(source.read_text(encoding="utf-8"), malformed)
            self.assertEqual(
                report["summary"][
                    "raw_iterable_map_entry_lambda_cast_action_count"
                ],
                0,
            )

    def test_raw_iterable_entry_lambda_fails_on_filter_signature_drift(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._fixture(root, filter_drift=True)
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            malformed = self._malformed_source()
            source.write_text(malformed, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)

            self.assertEqual(source.read_text(encoding="utf-8"), malformed)
            self.assertEqual(
                report["summary"][
                    "raw_iterable_map_entry_lambda_cast_action_count"
                ],
                0,
            )

    def test_raw_iterable_entry_lambda_fails_on_multiplicity_drift(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._fixture(root, duplicate=True)
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            malformed = self._malformed_source(include_second=False)
            source.write_text(malformed, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)

            self.assertEqual(source.read_text(encoding="utf-8"), malformed)
            self.assertEqual(
                report["summary"][
                    "raw_iterable_map_entry_lambda_cast_action_count"
                ],
                0,
            )

    def test_raw_iterable_entry_lambda_custom_sam_overloads_match_production_shape(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "p/Nonnull.java": (
                        "package p;\n"
                        "import java.lang.annotation.ElementType;\n"
                        "import java.lang.annotation.Retention;\n"
                        "import java.lang.annotation.RetentionPolicy;\n"
                        "import java.lang.annotation.Target;\n"
                        "@Retention(RetentionPolicy.RUNTIME)\n"
                        "@Target(ElementType.PARAMETER)\n"
                        "public @interface Nonnull {}\n"
                    ),
                    "p/W.java": (
                        "package p;\n"
                        "@FunctionalInterface\n"
                        "public interface W<T> {\n"
                        "    boolean a(T value);\n"
                        "}\n"
                    ),
                    "p/cb.java": (
                        "package p;\n"
                        "import java.util.Collections;\n"
                        "import java.util.Iterator;\n"
                        "public final class cb<T> implements Iterable<T> {\n"
                        "    public Iterator<T> iterator() {\n"
                        "        return Collections.<T>emptyList().iterator();\n"
                        "    }\n"
                        "}\n"
                    ),
                    "p/cv.java": (
                        "package p;\n"
                        "import java.util.Map;\n"
                        "public final class cv<K, V> {\n"
                        "    public cb<Map.Entry<K, V>> B() {\n"
                        "        return new cb<>();\n"
                        "    }\n"
                        "    public static <K, V> cv<K, V> b(\n"
                        "            Iterable<? extends Map.Entry<? extends K, "
                        "? extends V>> values) {\n"
                        "        return new cv<>();\n"
                        "    }\n"
                        "}\n"
                    ),
                    "p/db.java": (
                        "package p;\n"
                        "public final class db {\n"
                        "    public static <T> Iterable<T> c(\n"
                        "            Iterable<T> values, W<? super T> predicate) {\n"
                        "        return values;\n"
                        "    }\n"
                        "}\n"
                    ),
                    "p/EventBus.java": (
                        "package p;\n"
                        "public class EventBus {\n"
                        "    public static final class Subscriber {\n"
                        "        private final Object object;\n"
                        "        public Subscriber(Object object) { this.object = object; }\n"
                        "        public Object getObject() { return this.object; }\n"
                        "    }\n"
                        "    private cv<Class<?>, Subscriber> subscribers = new cv<>();\n"
                        "    public void unregister(@Nonnull final Object o) {\n"                        "        this.subscribers = cv.b(db.c(this.subscribers.B(), "
                        "entry -> entry.getValue().getObject() != o));\n"
                        "    }\n"
                        "    public void unregister(Subscriber subscriber) {\n"
                        "        this.subscribers = cv.b(db.c(this.subscribers.B(), "
                        "entry -> subscriber != entry.getValue()));\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )
            source = root / "src" / "p" / "EventBus.java"
            source.parent.mkdir(parents=True)
            malformed = (
                "package p;\n"
                "public class EventBus {\n"
                "    public static final class Subscriber {\n"
                "        private final Object object;\n"
                "        public Subscriber(Object object) { this.object = object; }\n"
                "        public Object getObject() { return this.object; }\n"
                "    }\n"
                "    private cv<Class<?>, Subscriber> subscribers = new cv<>();\n"
                "    public void unregister(@Nonnull final Object o) {\n"                "        this.subscribers = (cv<Class<?>, Subscriber>)cv.b("
                "db.c((Iterable)this.subscribers.B(), "
                "entry -> entry.getValue().getObject() != o));\n"
                "    }\n"
                "    public void unregister(Subscriber subscriber) {\n"
                "        this.subscribers = (cv<Class<?>, Subscriber>)cv.b("
                "db.c((Iterable)this.subscribers.B(), "
                "entry -> subscriber != entry.getValue()));\n"
                "    }\n"
                "}\n"
            )
            source.write_text(malformed, encoding="utf-8")

            before = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "before-production-entry-lambda"),
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(before.returncode, 0)
            self.assertIn("getValue", before.stderr)

            report = normalize_procyon_source(root / "src", jar)
            normalized = source.read_text(encoding="utf-8")
            self.assertEqual(
                normalized.count("(Iterable)this.subscribers.B()"),
                0,
            )
            actions = [
                row
                for row in report["actions"]
                if row["kind"]
                == "raw_iterable_map_entry_lambda_cast_removal"
            ]
            self.assertEqual(len(actions), 2)
            self.assertEqual(
                {row["method_name"] for row in actions},
                {"unregister"},
            )
            self.assertTrue(
                all(row["functional_owner"] == "p/W" for row in actions)
            )
            helper_descriptors = {
                row["lambda_bootstraps"][0]["helper_descriptor"]
                for row in actions
            }
            self.assertIn(
                "(Ljava/lang/Object;Ljava/util/Map$Entry;)Z",
                helper_descriptors,
            )
            self.assertIn(
                "(Lp/EventBus$Subscriber;Ljava/util/Map$Entry;)Z",
                helper_descriptors,
            )

            after = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "after-production-entry-lambda"),
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(after.returncode, 0, after.stderr)


class ErasedSetIntEnhancedForTests(unittest.TestCase):
    def _fixture(self, root: Path, *, exact_drift: bool = False) -> Path:
        value_type = "Long" if exact_drift else "Integer"
        loop_type = "long" if exact_drift else "int"
        add_expr = "(int)value" if exact_drift else "value"
        return _compile_java_fixture(
            root,
            {
                "p/A.java": (
                    "package p;\n"
                    "import java.util.LinkedHashSet;\n"
                    "import java.util.Set;\n"
                    "public class A {\n"
                    "    public static int sum() {\n"
                    f"        Set<{value_type}> set = new LinkedHashSet<>();\n"
                    f"        set.add({value_type}.valueOf(7));\n"
                    "        int total = 0;\n"
                    f"        for ({loop_type} value : set) {{\n"
                    f"            total += {add_expr};\n"
                    "        }\n"
                    "        return total;\n"
                    "    }\n"
                    "}\n"
                )
            },
        )

    def test_erased_set_int_enhanced_for_restores_iterable_type(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._fixture(root)
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package p;\n"
                "import java.util.LinkedHashSet;\n"
                "import java.util.Set;\n"
                "public class A {\n"
                "    public static int sum() {\n"
                "        Set set = new LinkedHashSet();\n"
                "        set.add(Integer.valueOf(7));\n"
                "        int total = 0;\n"
                "        for (int value : set) {\n"
                "            total += value;\n"
                "        }\n"
                "        return total;\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )

            before = subprocess.run(
                ["javac", "-d", str(root / "before-set-int"), str(source)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(before.returncode, 0)

            report = normalize_procyon_source(root / "src", jar)
            normalized = source.read_text(encoding="utf-8")
            self.assertIn(
                "for (int value : ((java.util.Set<Integer>)set))",
                normalized,
            )
            action = next(
                row
                for row in report["actions"]
                if row["kind"]
                == "erased_set_int_enhanced_for_reconstruction"
            )
            self.assertEqual(action["replacement_count"], 1)
            self.assertEqual(action["exact_integer_unbox_flow_count"], 1)

            after = subprocess.run(
                ["javac", "-d", str(root / "after-set-int"), str(source)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(after.returncode, 0, after.stderr)


    def test_erased_set_int_enhanced_for_accepts_raw_linkedhashset_source(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._fixture(root)
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package p;\n"
                "import java.util.LinkedHashSet;\n"
                "public class A {\n"
                "    public static int sum() {\n"
                "        LinkedHashSet set = new LinkedHashSet();\n"
                "        set.add(Integer.valueOf(7));\n"
                "        int total = 0;\n"
                "        for (int value : set) {\n"
                "            total += value;\n"
                "        }\n"
                "        return total;\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )

            before = subprocess.run(
                ["javac", "-d", str(root / "before-linked-set"), str(source)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(before.returncode, 0)

            report = normalize_procyon_source(root / "src", jar)
            normalized = source.read_text(encoding="utf-8")
            self.assertIn(
                "for (int value : ((java.util.Set<Integer>)set))",
                normalized,
            )
            action = next(
                row
                for row in report["actions"]
                if row["kind"]
                == "erased_set_int_enhanced_for_reconstruction"
            )
            self.assertEqual(
                action["iterable_declaration_types"],
                {"set": "LinkedHashSet"},
            )

            after = subprocess.run(
                ["javac", "-d", str(root / "after-linked-set"), str(source)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(after.returncode, 0, after.stderr)

    def test_erased_set_int_enhanced_for_fails_closed_on_unrelated_iterator(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "p/A.java": (
                        "package p;\n"
                        "import java.util.ArrayList;\n"
                        "import java.util.Iterator;\n"
                        "import java.util.LinkedHashSet;\n"
                        "import java.util.List;\n"
                        "import java.util.Set;\n"
                        "public class A {\n"
                        "    public static int sum() {\n"
                        "        Set<Integer> set = new LinkedHashSet<>();\n"
                        "        set.add(Integer.valueOf(7));\n"
                        "        int total = 0;\n"
                        "        for (int value : set) { total += value; }\n"
                        "        List<String> extra = new ArrayList<>();\n"
                        "        extra.add(\"x\");\n"
                        "        Iterator<String> it = extra.iterator();\n"
                        "        String ignored = it.next();\n"
                        "        return total + ignored.length() - 1;\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            malformed = (
                "package p;\n"
                "import java.util.LinkedHashSet;\n"
                "import java.util.Set;\n"
                "public class A {\n"
                "    public static int sum() {\n"
                "        Set set = new LinkedHashSet();\n"
                "        int total = 0;\n"
                "        for (int value : set) { total += value; }\n"
                "        return total;\n"
                "    }\n"
                "}\n"
            )
            source.write_text(malformed, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)
            self.assertEqual(source.read_text(encoding="utf-8"), malformed)
            self.assertFalse(
                any(
                    row["kind"]
                    == "erased_set_int_enhanced_for_reconstruction"
                    for row in report["actions"]
                )
            )

    def test_erased_set_int_enhanced_for_fails_closed_on_exact_drift(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._fixture(root, exact_drift=True)
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            malformed = (
                "package p;\n"
                "import java.util.LinkedHashSet;\n"
                "import java.util.Set;\n"
                "public class A {\n"
                "    public static int sum() {\n"
                "        Set set = new LinkedHashSet();\n"
                "        set.add(Integer.valueOf(7));\n"
                "        int total = 0;\n"
                "        for (int value : set) { total += value; }\n"
                "        return total;\n"
                "    }\n"
                "}\n"
            )
            source.write_text(malformed, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)
            self.assertEqual(source.read_text(encoding="utf-8"), malformed)
            self.assertFalse(
                any(
                    row["kind"]
                    == "erased_set_int_enhanced_for_reconstruction"
                    for row in report["actions"]
                )
            )




class ErasedMapKeySetIntEnhancedForTests(unittest.TestCase):
    def _fixture(
        self,
        root: Path,
        *,
        exact_drift: bool = False,
    ) -> Path:
        value_type = "Long" if exact_drift else "Integer"
        loop_type = "long" if exact_drift else "int"
        return _compile_java_fixture(
            root,
            {
                "p/A.java": (
                    "package p;\n"
                    "import java.util.Map;\n"
                    "public class A {\n"
                    "    public static int sum(Object input) {\n"
                    "        Map<" + value_type + ", Object> map = "
                    "(Map<" + value_type + ", Object>)input;\n"
                    "        int total = 0;\n"
                    "        for (" + loop_type + " value : map.keySet()) {\n"
                    "            total += (int)value;\n"
                    "        }\n"
                    "        return total;\n"
                    "    }\n"
                    "}\n"
                ),
            },
        )

    def test_map_keyset_int_enhanced_for_restores_iterable_type(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._fixture(root)
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package p;\n"
                "import java.util.Map;\n"
                "public class A {\n"
                "    public static int sum(Object input) {\n"
                "        Map map = (Map)input;\n"
                "        int total = 0;\n"
                "        for (final int value : map.keySet()) {\n"
                "            total += value;\n"
                "        }\n"
                "        return total;\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )

            before = subprocess.run(
                ["javac", "-d", str(root / "before-map-keyset"), str(source)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(before.returncode, 0)

            report = normalize_procyon_source(root / "src", jar)
            normalized = source.read_text(encoding="utf-8")
            self.assertIn(
                "for (final int value : "
                "((java.util.Set<Integer>)map.keySet()))",
                normalized,
            )
            action = next(
                row
                for row in report["actions"]
                if row["kind"]
                == "erased_map_keyset_int_enhanced_for_reconstruction"
            )
            self.assertEqual(action["receiver_names"], ["map"])
            self.assertEqual(action["replacement_count"], 1)
            self.assertEqual(action["exact_map_keyset_call_count"], 1)
            self.assertEqual(action["flows"][0]["receiver"]["kind"], "local")
            self.assertGreaterEqual(
                action["flows"][0]["receiver"]["local_slot"],
                0,
            )
            self.assertEqual(
                report["summary"][
                    "erased_map_keyset_int_enhanced_for_action_count"
                ],
                1,
            )
            self.assertEqual(
                report["summary"][
                    "erased_map_keyset_int_enhanced_for_reference_count"
                ],
                1,
            )

            after = subprocess.run(
                ["javac", "-d", str(root / "after-map-keyset"), str(source)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(after.returncode, 0, after.stderr)

    def test_map_keyset_int_enhanced_for_ignores_unrelated_keyset_flow(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "p/A.java": (
                        "package p;\n"
                        "import java.util.LinkedHashMap;\n"
                        "import java.util.Map;\n"
                        "public class A {\n"
                        "    public static int sum(Object input) {\n"
                        "        Map<String, Object> extra = new LinkedHashMap<>();\n"
                        "        extra.put(\"x\", new Object());\n"
                        "        int total = 0;\n"
                        "        for (String ignored : extra.keySet()) {\n"
                        "            total += ignored.length() - 1;\n"
                        "        }\n"
                        "        Map<Integer, Object> map = "
                        "(Map<Integer, Object>)input;\n"
                        "        for (int value : map.keySet()) {\n"
                        "            total += value;\n"
                        "        }\n"
                        "        return total;\n"
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
                "import java.util.Map;\n"
                "public class A {\n"
                "    public static int sum(Object input) {\n"
                "        Map<String, Object> extra = new LinkedHashMap<>();\n"
                "        extra.put(\"x\", new Object());\n"
                "        int total = 0;\n"
                "        for (String ignored : extra.keySet()) {\n"
                "            total += ignored.length() - 1;\n"
                "        }\n"
                "        Map map = (Map)input;\n"
                "        for (final int value : map.keySet()) {\n"
                "            total += value;\n"
                "        }\n"
                "        return total;\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )

            report = normalize_procyon_source(root / "src", jar)
            normalized = source.read_text(encoding="utf-8")
            self.assertIn(
                "for (final int value : "
                "((java.util.Set<Integer>)map.keySet()))",
                normalized,
            )
            action = next(
                row
                for row in report["actions"]
                if row["kind"]
                == "erased_map_keyset_int_enhanced_for_reconstruction"
            )
            self.assertEqual(action["exact_map_keyset_call_count"], 2)
            self.assertEqual(action["exact_proven_map_keyset_flow_count"], 1)
            self.assertEqual(action["replacement_count"], 1)

            after = subprocess.run(
                ["javac", "-d", str(root / "after-map-keyset-extra"), str(source)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(after.returncode, 0, after.stderr)

    def test_map_keyset_int_enhanced_for_fails_closed_on_element_drift(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._fixture(root, exact_drift=True)
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            malformed = (
                "package p;\n"
                "import java.util.Map;\n"
                "public class A {\n"
                "    public static int sum(Object input) {\n"
                "        Map map = (Map)input;\n"
                "        int total = 0;\n"
                "        for (int value : map.keySet()) {\n"
                "            total += value;\n"
                "        }\n"
                "        return total;\n"
                "    }\n"
                "}\n"
            )
            source.write_text(malformed, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)

            self.assertEqual(source.read_text(encoding="utf-8"), malformed)
            self.assertEqual(
                report["summary"][
                    "erased_map_keyset_int_enhanced_for_action_count"
                ],
                0,
            )

    def test_map_keyset_int_enhanced_for_fails_closed_without_raw_map(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._fixture(root)
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            original = (
                "package p;\n"
                "import java.util.Map;\n"
                "public class A {\n"
                "    public static int sum(Object input) {\n"
                "        Map<Integer, Object> map = "
                "(Map<Integer, Object>)input;\n"
                "        int total = 0;\n"
                "        for (int value : map.keySet()) {\n"
                "            total += value;\n"
                "        }\n"
                "        return total;\n"
                "    }\n"
                "}\n"
            )
            source.write_text(original, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)

            self.assertEqual(source.read_text(encoding="utf-8"), original)
            self.assertEqual(
                report["summary"][
                    "erased_map_keyset_int_enhanced_for_action_count"
                ],
                0,
            )




    def test_map_keyset_int_enhanced_for_rejects_stale_local_provenance(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "p/A.java": (
                        "package p;\n"
                        "import java.util.Collections;\n"
                        "import java.util.Map;\n"
                        "public class A {\n"
                        "    public static int sum(Object input) {\n"
                        "        Map<Integer, Object> map = "
                        "(Map<Integer, Object>)input;\n"
                        "        map = Collections.emptyMap();\n"
                        "        int total = 0;\n"
                        "        for (int value : map.keySet()) {\n"
                        "            total += value;\n"
                        "        }\n"
                        "        return total;\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            malformed = (
                "package p;\n"
                "import java.util.Map;\n"
                "public class A {\n"
                "    public static int sum(Object input) {\n"
                "        Map map = (Map)input;\n"
                "        int total = 0;\n"
                "        for (int value : map.keySet()) {\n"
                "            total += value;\n"
                "        }\n"
                "        return total;\n"
                "    }\n"
                "}\n"
            )
            source.write_text(malformed, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)

            self.assertEqual(source.read_text(encoding="utf-8"), malformed)
            self.assertEqual(
                report["summary"][
                    "erased_map_keyset_int_enhanced_for_action_count"
                ],
                0,
            )

class ErasedListIntegerEnhancedForTests(unittest.TestCase):
    def _fixture(
        self,
        root: Path,
        *,
        exact_drift: bool = False,
    ) -> Path:
        element_type = "Long" if exact_drift else "Integer"
        add_values = (
            "        values.add(Long.valueOf(1L));\n"
            "        values.add(Long.valueOf(2L));\n"
            if exact_drift
            else
            "        values.add(Integer.valueOf(1));\n"
            "        values.add(Integer.valueOf(2));\n"
        )
        body = (
            "            total += value.intValue();\n"
            if not exact_drift
            else
            "            total += value.intValue();\n"
        )
        return _compile_java_fixture(
            root,
            {
                "p/A.java": (
                    "package p;\n"
                    "import java.util.ArrayList;\n"
                    "import java.util.List;\n"
                    "public class A {\n"
                    "    public static int sum() {\n"
                    "        List<" + element_type + "> values = "
                    "new ArrayList<>();\n"
                    + add_values
                    + "        int total = 0;\n"
                    "        for (" + element_type + " value : values) {\n"
                    + body
                    + "        }\n"
                    "        for (" + element_type + " value : values) {\n"
                    + body
                    + "        }\n"
                    "        return total;\n"
                    "    }\n"
                    "}\n"
                ),
            },
        )

    def test_raw_list_integer_enhanced_for_restores_iterable_type(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._fixture(root)
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package p;\n"
                "import java.util.ArrayList;\n"
                "import java.util.List;\n"
                "public class A {\n"
                "    public static int sum() {\n"
                "        List values = new ArrayList();\n"
                "        values.add(Integer.valueOf(1));\n"
                "        values.add(Integer.valueOf(2));\n"
                "        int total = 0;\n"
                "        for (final Integer value : values) {\n"
                "            total += value.intValue();\n"
                "        }\n"
                "        for (final Integer value : values) {\n"
                "            total += value.intValue();\n"
                "        }\n"
                "        return total;\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )

            before = subprocess.run(
                ["javac", "-d", str(root / "before-list-integer"), str(source)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(before.returncode, 0)

            report = normalize_procyon_source(root / "src", jar)
            normalized = source.read_text(encoding="utf-8")
            self.assertEqual(
                normalized.count(
                    "((java.util.List<Integer>)values)"
                ),
                2,
            )
            action = next(
                row
                for row in report["actions"]
                if row["kind"]
                == "erased_list_integer_enhanced_for_reconstruction"
            )
            self.assertEqual(action["iterable_name"], "values")
            self.assertEqual(action["replacement_count"], 2)
            self.assertEqual(action["exact_list_iterator_call_count"], 2)
            self.assertEqual(len(action["flows"]), 2)
            self.assertEqual(
                report["summary"][
                    "erased_list_integer_enhanced_for_action_count"
                ],
                1,
            )
            self.assertEqual(
                report["summary"][
                    "erased_list_integer_enhanced_for_reference_count"
                ],
                2,
            )

            after = subprocess.run(
                ["javac", "-d", str(root / "after-list-integer"), str(source)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(after.returncode, 0, after.stderr)

    def test_raw_list_integer_enhanced_for_ignores_unrelated_iterator(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "p/A.java": (
                        "package p;\n"
                        "import java.util.ArrayList;\n"
                        "import java.util.List;\n"
                        "public class A {\n"
                        "    public static int sum() {\n"
                        "        List<String> extra = new ArrayList<>();\n"
                        "        extra.add(\"x\");\n"
                        "        int total = 0;\n"
                        "        for (String ignored : extra) {\n"
                        "            total += ignored.length() - 1;\n"
                        "        }\n"
                        "        List<Integer> values = new ArrayList<>();\n"
                        "        values.add(Integer.valueOf(1));\n"
                        "        values.add(Integer.valueOf(2));\n"
                        "        for (Integer value : values) {\n"
                        "            total += value.intValue();\n"
                        "        }\n"
                        "        for (Integer value : values) {\n"
                        "            total += value.intValue();\n"
                        "        }\n"
                        "        return total;\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package p;\n"
                "import java.util.ArrayList;\n"
                "import java.util.List;\n"
                "public class A {\n"
                "    public static int sum() {\n"
                "        List<String> extra = new ArrayList<>();\n"
                "        extra.add(\"x\");\n"
                "        int total = 0;\n"
                "        for (String ignored : extra) {\n"
                "            total += ignored.length() - 1;\n"
                "        }\n"
                "        List values = new ArrayList();\n"
                "        values.add(Integer.valueOf(1));\n"
                "        values.add(Integer.valueOf(2));\n"
                "        for (final Integer value : values) {\n"
                "            total += value.intValue();\n"
                "        }\n"
                "        for (final Integer value : values) {\n"
                "            total += value.intValue();\n"
                "        }\n"
                "        return total;\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )

            report = normalize_procyon_source(root / "src", jar)
            normalized = source.read_text(encoding="utf-8")
            self.assertEqual(
                normalized.count("((java.util.List<Integer>)values)"),
                2,
            )
            action = next(
                row
                for row in report["actions"]
                if row["kind"]
                == "erased_list_integer_enhanced_for_reconstruction"
            )
            self.assertEqual(action["exact_list_iterator_call_count"], 3)
            self.assertEqual(action["exact_proven_list_integer_flow_count"], 2)
            self.assertEqual(action["replacement_count"], 2)

            after = subprocess.run(
                ["javac", "-d", str(root / "after-list-integer-extra"), str(source)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(after.returncode, 0, after.stderr)

    def test_raw_list_integer_enhanced_for_fails_closed_on_element_drift(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._fixture(root, exact_drift=True)
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            malformed = (
                "package p;\n"
                "import java.util.ArrayList;\n"
                "import java.util.List;\n"
                "public class A {\n"
                "    public static int sum() {\n"
                "        List values = new ArrayList();\n"
                "        int total = 0;\n"
                "        for (Integer value : values) {\n"
                "            total += value.intValue();\n"
                "        }\n"
                "        for (Integer value : values) {\n"
                "            total += value.intValue();\n"
                "        }\n"
                "        return total;\n"
                "    }\n"
                "}\n"
            )
            source.write_text(malformed, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)

            self.assertEqual(source.read_text(encoding="utf-8"), malformed)
            self.assertEqual(
                report["summary"][
                    "erased_list_integer_enhanced_for_action_count"
                ],
                0,
            )

    def test_raw_list_integer_enhanced_for_refuses_parameterized_source(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._fixture(root)
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            original = (
                "package p;\n"
                "import java.util.ArrayList;\n"
                "import java.util.List;\n"
                "public class A {\n"
                "    public static int sum() {\n"
                "        List<Integer> values = new ArrayList<>();\n"
                "        int total = 0;\n"
                "        for (Integer value : values) {\n"
                "            total += value.intValue();\n"
                "        }\n"
                "        for (Integer value : values) {\n"
                "            total += value.intValue();\n"
                "        }\n"
                "        return total;\n"
                "    }\n"
                "}\n"
            )
            source.write_text(original, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)

            self.assertEqual(source.read_text(encoding="utf-8"), original)
            self.assertEqual(
                report["summary"][
                    "erased_list_integer_enhanced_for_action_count"
                ],
                0,
            )




    def test_raw_list_integer_enhanced_for_rejects_stale_local_provenance(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "p/A.java": (
                        "package p;\n"
                        "import java.util.Collections;\n"
                        "import java.util.List;\n"
                        "public class A {\n"
                        "    public static int sum(Object input) {\n"
                        "        List<Integer> values = "
                        "(List<Integer>)input;\n"
                        "        values = Collections.emptyList();\n"
                        "        int total = 0;\n"
                        "        for (Integer value : values) {\n"
                        "            total += value.intValue();\n"
                        "        }\n"
                        "        return total;\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            malformed = (
                "package p;\n"
                "import java.util.List;\n"
                "public class A {\n"
                "    public static int sum(Object input) {\n"
                "        List values = (List)input;\n"
                "        int total = 0;\n"
                "        for (Integer value : values) {\n"
                "            total += value.intValue();\n"
                "        }\n"
                "        return total;\n"
                "    }\n"
                "}\n"
            )
            source.write_text(malformed, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)

            self.assertEqual(source.read_text(encoding="utf-8"), malformed)
            self.assertEqual(
                report["summary"][
                    "erased_list_integer_enhanced_for_action_count"
                ],
                0,
            )

class ErasedIteratorAssignmentCastTests(unittest.TestCase):
    def _fixture(self, root: Path, *, exact_drift: bool = False) -> Path:
        target = "Other" if exact_drift else "Value"
        return _compile_java_fixture(
            root,
            {
                "p/Value.java": (
                    "package p;\n"
                    "public class Value {}\n"
                ),
                "p/Other.java": (
                    "package p;\n"
                    "public class Other {}\n"
                ),
                "p/Current.java": (
                    "package p;\n"
                    "import java.util.ArrayList;\n"
                    "import java.util.Iterator;\n"
                    "import java.util.List;\n"
                    "public class Current {\n"
                    f"    public static {target} first() {{\n"
                    f"        List<{target}> values = new ArrayList<>();\n"
                    f"        values.add(new {target}());\n"
                    f"        Iterator<{target}> iterator = values.iterator();\n"
                    f"        {target} value = iterator.next();\n"
                    "        return value;\n"
                    "    }\n"
                    "}\n"
                ),
            },
        )

    def test_erased_iterator_assignment_restores_exact_cast(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._fixture(root)
            source = root / "src" / "p" / "Current.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package p;\n"
                "import java.util.ArrayList;\n"
                "import java.util.Iterator;\n"
                "import java.util.List;\n"
                "public class Current {\n"
                "    public static Value first() {\n"
                "        List values = new ArrayList();\n"
                "        values.add(new Value());\n"
                "        Iterator iterator = values.iterator();\n"
                "        final Value value = iterator.next();\n"
                "        return value;\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )

            before = subprocess.run(
                [
                    "javac", "-cp", str(jar), "-d",
                    str(root / "before-iterator-cast"), str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(before.returncode, 0)

            report = normalize_procyon_source(root / "src", jar)
            normalized = source.read_text(encoding="utf-8")
            self.assertIn(
                "final Value value = (Value)iterator.next();",
                normalized,
            )
            action = next(
                row
                for row in report["actions"]
                if row["kind"]
                == "erased_iterator_assignment_cast_reconstruction"
            )
            self.assertEqual(action["replacement_count"], 1)
            self.assertEqual(action["exact_checkcast_types"], ["p/Value"])

            after = subprocess.run(
                [
                    "javac", "-cp", str(jar), "-d",
                    str(root / "after-iterator-cast"), str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(after.returncode, 0, after.stderr)

    def test_erased_iterator_assignment_uses_lambda_helper_checkcast(
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
                    "p/Current.java": (
                        "package p;\n"
                        "import java.util.ArrayList;\n"
                        "import java.util.Iterator;\n"
                        "import java.util.List;\n"
                        "public class Current {\n"
                        "    public static Value first() {\n"
                        "        List<Value> values = new ArrayList<>();\n"
                        "        values.add(new Value());\n"
                        "        Runnable task = () -> {\n"
                        "            Iterator<Value> iterator = "
                        "values.iterator();\n"
                        "            Value value = iterator.next();\n"
                        "            if (value == null) throw "
                        "new IllegalStateException();\n"
                        "        };\n"
                        "        task.run();\n"
                        "        return values.get(0);\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )
            source = root / "src" / "p" / "Current.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package p;\n"
                "import java.util.ArrayList;\n"
                "import java.util.Iterator;\n"
                "import java.util.List;\n"
                "public class Current {\n"
                "    public static Value first() {\n"
                "        List<Value> values = new ArrayList<>();\n"
                "        values.add(new Value());\n"
                "        Runnable task = () -> {\n"
                "            Iterator iterator = values.iterator();\n"
                "            final Value value = iterator.next();\n"
                "            if (value == null) throw "
                "new IllegalStateException();\n"
                "        };\n"
                "        task.run();\n"
                "        return values.get(0);\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )

            before = subprocess.run(
                [
                    "javac", "-cp", str(jar), "-d",
                    str(root / "before-iterator-lambda"), str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(before.returncode, 0)

            report = normalize_procyon_source(root / "src", jar)
            normalized = source.read_text(encoding="utf-8")
            self.assertIn(
                "final Value value = (Value)iterator.next();",
                normalized,
            )
            action = next(
                row
                for row in report["actions"]
                if row["kind"]
                == "erased_iterator_assignment_cast_reconstruction"
            )
            self.assertEqual(action["proof_scope"], "lambda_helper")
            self.assertEqual(action["exact_checkcast_types"], ["p/Value"])
            self.assertEqual(len(action["lambda_helpers"]), 1)

            after = subprocess.run(
                [
                    "javac", "-cp", str(jar), "-d",
                    str(root / "after-iterator-lambda"), str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(after.returncode, 0, after.stderr)

    def test_erased_iterator_assignment_lambda_helper_type_drift_fails_closed(
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
                    "p/Other.java": (
                        "package p;\n"
                        "public class Other {}\n"
                    ),
                    "p/Current.java": (
                        "package p;\n"
                        "import java.util.ArrayList;\n"
                        "import java.util.Iterator;\n"
                        "import java.util.List;\n"
                        "public class Current {\n"
                        "    public static Other first() {\n"
                        "        List<Other> values = new ArrayList<>();\n"
                        "        values.add(new Other());\n"
                        "        Runnable task = () -> {\n"
                        "            Iterator<Other> iterator = "
                        "values.iterator();\n"
                        "            Other value = iterator.next();\n"
                        "            if (value == null) throw "
                        "new IllegalStateException();\n"
                        "        };\n"
                        "        task.run();\n"
                        "        return values.get(0);\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )
            source = root / "src" / "p" / "Current.java"
            source.parent.mkdir(parents=True)
            malformed = (
                "package p;\n"
                "import java.util.Iterator;\n"
                "import java.util.List;\n"
                "public class Current {\n"
                "    public static Other first() {\n"
                "        List<Other> values = null;\n"
                "        Runnable task = () -> {\n"
                "            Iterator iterator = values.iterator();\n"
                "            final Value value = iterator.next();\n"
                "        };\n"
                "        task.run();\n"
                "        return null;\n"
                "    }\n"
                "}\n"
            )
            source.write_text(malformed, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)
            self.assertEqual(source.read_text(encoding="utf-8"), malformed)
            self.assertFalse(
                any(
                    row["kind"]
                    == "erased_iterator_assignment_cast_reconstruction"
                    for row in report["actions"]
                )
            )

    def test_erased_iterator_assignment_fails_closed_on_extra_exact_flow(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "p/Value.java": (
                        "package p;\n"
                        "public class Value {}\n"
                    ),
                    "p/Current.java": (
                        "package p;\n"
                        "import java.util.ArrayList;\n"
                        "import java.util.Iterator;\n"
                        "import java.util.List;\n"
                        "public class Current {\n"
                        "    public static Value first() {\n"
                        "        List<Value> values = new ArrayList<>();\n"
                        "        values.add(new Value());\n"
                        "        values.add(new Value());\n"
                        "        Iterator<Value> iterator = values.iterator();\n"
                        "        Value first = iterator.next();\n"
                        "        Value second = iterator.next();\n"
                        "        return first != null ? first : second;\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )
            source = root / "src" / "p" / "Current.java"
            source.parent.mkdir(parents=True)
            malformed = (
                "package p;\n"
                "import java.util.ArrayList;\n"
                "import java.util.Iterator;\n"
                "import java.util.List;\n"
                "public class Current {\n"
                "    public static Value first() {\n"
                "        List values = new ArrayList();\n"
                "        Iterator iterator = values.iterator();\n"
                "        final Value value = iterator.next();\n"
                "        return value;\n"
                "    }\n"
                "}\n"
            )
            source.write_text(malformed, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)
            self.assertEqual(source.read_text(encoding="utf-8"), malformed)
            self.assertFalse(
                any(
                    row["kind"]
                    == "erased_iterator_assignment_cast_reconstruction"
                    for row in report["actions"]
                )
            )


    def test_erased_iterator_assignment_fq_type_requires_exact_owner(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "p/Value.java": (
                        "package p;\n"
                        "public class Value {}\n"
                    ),
                    "q/Value.java": (
                        "package q;\n"
                        "public class Value {}\n"
                    ),
                    "p/Current.java": (
                        "package p;\n"
                        "import java.util.ArrayList;\n"
                        "import java.util.Iterator;\n"
                        "import java.util.List;\n"
                        "public class Current {\n"
                        "    public static q.Value first() {\n"
                        "        List<q.Value> values = new ArrayList<>();\n"
                        "        values.add(new q.Value());\n"
                        "        Iterator<q.Value> iterator = values.iterator();\n"
                        "        q.Value value = iterator.next();\n"
                        "        return value;\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )
            source = root / "src" / "p" / "Current.java"
            source.parent.mkdir(parents=True)
            malformed = (
                "package p;\n"
                "import java.util.Iterator;\n"
                "public class Current {\n"
                "    public static q.Value first() {\n"
                "        Iterator iterator = null;\n"
                "        final p.Value value = iterator.next();\n"
                "        return null;\n"
                "    }\n"
                "}\n"
            )
            source.write_text(malformed, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)
            self.assertEqual(source.read_text(encoding="utf-8"), malformed)
            self.assertFalse(
                any(
                    row["kind"]
                    == "erased_iterator_assignment_cast_reconstruction"
                    for row in report["actions"]
                )
            )

    def test_erased_iterator_assignment_fails_closed_on_checkcast_drift(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._fixture(root, exact_drift=True)
            source = root / "src" / "p" / "Current.java"
            source.parent.mkdir(parents=True)
            malformed = (
                "package p;\n"
                "import java.util.ArrayList;\n"
                "import java.util.Iterator;\n"
                "import java.util.List;\n"
                "public class Current {\n"
                "    public static Value first() {\n"
                "        List values = new ArrayList();\n"
                "        Iterator iterator = values.iterator();\n"
                "        final Value value = iterator.next();\n"
                "        return value;\n"
                "    }\n"
                "}\n"
            )
            source.write_text(malformed, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)
            self.assertEqual(source.read_text(encoding="utf-8"), malformed)
            self.assertFalse(
                any(
                    row["kind"]
                    == "erased_iterator_assignment_cast_reconstruction"
                    for row in report["actions"]
                )
            )


class MissingSyntheticBridgeForwarderTests(unittest.TestCase):
    def _malformed_source(self) -> str:
        return (
            "package p;\n"
            "import java.util.Map;\n"
            "public class F extends Base<R> {\n"
            "    public R b(int id, Map<String,Object> values) {\n"
            "        return new R();\n"
            "    }\n"
            "}\n"
        )

    def test_missing_synthetic_bridge_forwarder_is_reconstructed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _synthetic_bridge_forwarder_fixture(
                root,
                retarget_bridge=True,
            )

            with zipfile.ZipFile(jar) as z:
                profile = profile_class_field_accesses_exact(
                    z.read("p/F.class")
                )
            bridge = next(
                method
                for method in profile["methods"]
                if (
                    method["name"] == "a"
                    and method["descriptor"]
                    == "(ILjava/util/Map;)Ljava/lang/Object;"
                    and int(method["access"]) & 0x1000
                    and int(method["access"]) & 0x0040
                )
            )
            bridge_calls = [
                row
                for row in bridge["instructions"]
                if row.get("mnemonic") == "invokevirtual"
            ]
            self.assertEqual(len(bridge_calls), 1)
            self.assertEqual(bridge_calls[0]["owner"], "p/F")
            self.assertEqual(bridge_calls[0]["name"], "b")
            self.assertEqual(
                bridge_calls[0]["descriptor"],
                "(ILjava/util/Map;)Lp/R;",
            )

            source = root / "src" / "p" / "F.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                self._malformed_source(),
                encoding="utf-8",
            )

            before = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "before-synthetic-bridge"),
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
                "public R a(int id, Map<String,Object> values) {",
                normalized,
            )
            self.assertIn(
                "return this.b(id, values);",
                normalized,
            )
            action = next(
                row
                for row in report["actions"]
                if row["kind"]
                == "missing_synthetic_bridge_forwarder_reconstruction"
            )
            self.assertEqual(action["bridge_name"], "a")
            self.assertEqual(action["target_name"], "b")
            self.assertEqual(action["abstract_super_owner"], "p/Base")
            self.assertEqual(action["source_return_type"], "R")
            self.assertEqual(
                action["source_parameter_names"],
                ["id", "values"],
            )
            self.assertEqual(
                report["summary"][
                    "missing_synthetic_bridge_forwarder_action_count"
                ],
                1,
            )
            self.assertEqual(
                report["summary"][
                    "missing_synthetic_bridge_forwarder_method_count"
                ],
                1,
            )

            after = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "after-synthetic-bridge"),
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

    def test_missing_synthetic_bridge_forwarder_rejects_same_name_target(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _synthetic_bridge_forwarder_fixture(
                root,
                retarget_bridge=False,
            )
            source = root / "src" / "p" / "F.java"
            source.parent.mkdir(parents=True)
            malformed = self._malformed_source()
            source.write_text(malformed, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)

            self.assertEqual(
                source.read_text(encoding="utf-8"),
                malformed,
            )
            self.assertFalse(
                any(
                    row["kind"]
                    == "missing_synthetic_bridge_forwarder_reconstruction"
                    for row in report["actions"]
                )
            )




class ObjectBooleanConditionCastTests(unittest.TestCase):
    def _fixture(self, root: Path, *, boolean_unbox: bool = True) -> Path:
        condition = "(Boolean)value" if boolean_unbox else "value != null"
        return _compile_java_fixture(
            root,
            {
                "p/A.java": (
                    "package p;\n"
                    "public class A {\n"
                    "    public static int read() {\n"
                    "        Object value = Boolean.TRUE;\n"
                    "        if (" + condition + ") {\n"
                    "            return 1;\n"
                    "        }\n"
                    "        return 0;\n"
                    "    }\n"
                    "}\n"
                ),
            },
        )

    def test_object_boolean_condition_restores_exact_cast(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._fixture(root)
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package p;\n"
                "public class A {\n"
                "    public static int read() {\n"
                "        Object value = Boolean.TRUE;\n"
                "        if (value) {\n"
                "            return 1;\n"
                "        }\n"
                "        return 0;\n"
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
                    str(root / "before-object-boolean"),
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(before.returncode, 0)

            report = normalize_procyon_source(root / "src", jar)
            normalized = source.read_text(encoding="utf-8")
            self.assertIn("if ((Boolean)value) {", normalized)
            action = next(
                row
                for row in report["actions"]
                if row["kind"]
                == "object_boolean_condition_cast_reconstruction"
            )
            self.assertEqual(action["condition_names"], ["value"])
            self.assertEqual(action["replacement_count"], 1)
            self.assertEqual(
                report["summary"][
                    "object_boolean_condition_cast_action_count"
                ],
                1,
            )
            self.assertEqual(
                report["summary"][
                    "object_boolean_condition_cast_reference_count"
                ],
                1,
            )

            after = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "after-object-boolean"),
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

    def test_object_boolean_condition_fails_closed_without_exact_unbox(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._fixture(root, boolean_unbox=False)
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            malformed = (
                "package p;\n"
                "public class A {\n"
                "    public static int read() {\n"
                "        Object value = Boolean.TRUE;\n"
                "        if (value) {\n"
                "            return 1;\n"
                "        }\n"
                "        return 0;\n"
                "    }\n"
                "}\n"
            )
            source.write_text(malformed, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)
            self.assertEqual(source.read_text(encoding="utf-8"), malformed)
            self.assertFalse(
                any(
                    row["kind"]
                    == "object_boolean_condition_cast_reconstruction"
                    for row in report["actions"]
                )
            )




class ErasedMapGetIntegerTernaryTests(unittest.TestCase):
    def _fixture(
        self,
        root: Path,
        *,
        first_key: str = "fullClone",
    ) -> Path:
        return _compile_java_fixture(
            root,
            {
                "p/A.java": (
                    "package p;\n"
                    "import java.util.Map;\n"
                    "public class A {\n"
                    "    public static int read(Map<String, Object> map) {\n"
                    "        final int value = map.containsKey(\""
                    + first_key
                    + "\") ? ((int)map.get(\""
                    + first_key
                    + "\")) : ((int)map.get(\"clone\"));\n"
                    "        return value;\n"
                    "    }\n"
                    "}\n"
                ),
            },
        )

    def test_map_get_integer_ternary_restores_exact_first_arm_cast(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._fixture(root)
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                "package p;\n"
                "import java.util.Map;\n"
                "public class A {\n"
                "    public static int read(Map<String, Object> map) {\n"
                "        final int value = map.containsKey(\"fullClone\") "
                "? map.get(\"fullClone\") "
                ": ((int)map.get(\"clone\"));\n"
                "        return value;\n"
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
                    str(root / "before-map-ternary"),
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
                'map.containsKey("fullClone") '
                '? ((int)map.get("fullClone")) '
                ': ((int)map.get("clone"))',
                normalized,
            )
            action = next(
                row
                for row in report["actions"]
                if row["kind"]
                == "erased_map_get_integer_ternary_cast_reconstruction"
            )
            self.assertEqual(action["map_parameters"], ["map"])
            self.assertEqual(action["replacement_count"], 1)
            self.assertEqual(action["flows"][0]["key1"], "fullClone")
            self.assertEqual(action["flows"][0]["key2"], "clone")
            self.assertGreater(
                action["flows"][0]["second_arm_offset"],
                action["flows"][0]["selector_offset"],
            )
            self.assertGreater(
                action["flows"][0]["merge_offset"],
                action["flows"][0]["goto_offset"],
            )

            after = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "after-map-ternary"),
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

    def test_map_get_integer_ternary_fails_closed_on_key_drift(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._fixture(root, first_key="other")
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            malformed = (
                "package p;\n"
                "import java.util.Map;\n"
                "public class A {\n"
                "    public static int read(Map<String, Object> map) {\n"
                "        final int value = map.containsKey(\"fullClone\") "
                "? map.get(\"fullClone\") "
                ": ((int)map.get(\"clone\"));\n"
                "        return value;\n"
                "    }\n"
                "}\n"
            )
            source.write_text(malformed, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)
            self.assertEqual(source.read_text(encoding="utf-8"), malformed)
            self.assertFalse(
                any(
                    row["kind"]
                    == "erased_map_get_integer_ternary_cast_reconstruction"
                    for row in report["actions"]
                )
            )



class CcGenericValueObjectCastTests(unittest.TestCase):
    def _fixture(
        self,
        root: Path,
        *,
        field_value_type: str = "Boolean",
        generic_method: bool = True,
        duplicate_boolean_call: bool = False,
    ) -> Path:
        cc_method = (
            "    public V a(int key, V value) { return value; }\n"
            if generic_method
            else
            "    public Object a(int key, Object value) { return value; }\n"
        )
        if field_value_type == "Boolean":
            exact_call = "        A.flags.a(1, true);\n"
            if duplicate_boolean_call:
                exact_call += "        A.flags.a(2, false);\n"
        else:
            exact_call = "        A.flags.a(1, \"value\");\n"

        return _compile_java_fixture(
            root,
            {
                "gnu/trove/f/b/cc.java": (
                    "package gnu.trove.f.b;\n"
                    "public class cc<V> {\n"
                    + cc_method
                    + "}\n"
                ),
                "p/Value.java": (
                    "package p;\n"
                    "public class Value { public Value() {} }\n"
                ),
                "p/A.java": (
                    "package p;\n"
                    "import gnu.trove.f.b.cc;\n"
                    "public class A {\n"
                    "    public static cc<"
                    + field_value_type
                    + "> flags = new cc<>();\n"
                    "    public static cc<Value> values = new cc<>();\n"
                    "    public static boolean run(Value value) {\n"
                    + exact_call
                    + (
                        "        A.values.a(2, new Value());\n"
                        "        A.values.a(3, value);\n"
                        if field_value_type == "Boolean"
                        and generic_method
                        and not duplicate_boolean_call
                        else ""
                    )
                    + "        return true;\n"
                    "    }\n"
                    "}\n"
                ),
            },
        )

    def _malformed_source(self) -> str:
        return (
            "package p;\n"
            "import gnu.trove.f.b.cc;\n"
            "public class A {\n"
            "    public static cc<Boolean> flags = new cc<>();\n"
            "    public static cc<Value> values = new cc<>();\n"
            "    public static boolean run(Value value) {\n"
            "        A.flags.a(1, (Object)true);\n"
            "        A.values.a(2, (Object)new Value());\n"
            "        A.values.a(3, (Object)value);\n"
            "        return true;\n"
            "    }\n"
            "}\n"
        )

    def test_cc_generic_value_object_casts_restore_source_typing(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._fixture(root)
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                self._malformed_source(),
                encoding="utf-8",
            )

            before = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "before-cc-generic"),
                    str(source),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertNotEqual(before.returncode, 0)

            report = normalize_procyon_source(root / "src", jar)
            normalized = source.read_text(encoding="utf-8")
            self.assertIn("A.flags.a(1, true);", normalized)
            self.assertIn(
                "A.values.a(2, new Value());",
                normalized,
            )
            self.assertIn("A.values.a(3, value);", normalized)
            self.assertNotIn("(Object)true", normalized)
            self.assertNotIn("(Object)new Value()", normalized)
            self.assertNotIn("(Object)value", normalized)

            action = next(
                row
                for row in report["actions"]
                if row["kind"] == "cc_generic_value_object_cast_removal"
            )
            self.assertEqual(action["replacement_count"], 3)
            self.assertEqual(
                action["value_kinds"],
                ["boolean", "new", "identifier"],
            )
            self.assertEqual(
                report["summary"][
                    "cc_generic_value_object_cast_action_count"
                ],
                1,
            )
            self.assertEqual(
                report["summary"][
                    "cc_generic_value_object_cast_reference_count"
                ],
                3,
            )

            after = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "after-cc-generic"),
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

    def test_cc_generic_value_object_casts_fail_on_field_type_drift(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._fixture(root, field_value_type="String")
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            malformed = (
                "package p;\n"
                "import gnu.trove.f.b.cc;\n"
                "public class A {\n"
                "    public static cc<Boolean> flags = new cc<>();\n"
                "    public static boolean run(Value value) {\n"
                "        A.flags.a(1, (Object)true);\n"
                "        return true;\n"
                "    }\n"
                "}\n"
            )
            source.write_text(malformed, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)

            self.assertEqual(source.read_text(encoding="utf-8"), malformed)
            self.assertEqual(
                report["summary"][
                    "cc_generic_value_object_cast_action_count"
                ],
                0,
            )

    def test_cc_generic_value_object_casts_fail_without_method_signature(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._fixture(root, generic_method=False)
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            malformed = (
                "package p;\n"
                "import gnu.trove.f.b.cc;\n"
                "public class A {\n"
                "    public static cc<Boolean> flags = new cc<>();\n"
                "    public static boolean run(Value value) {\n"
                "        A.flags.a(1, (Object)true);\n"
                "        return true;\n"
                "    }\n"
                "}\n"
            )
            source.write_text(malformed, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)

            self.assertEqual(source.read_text(encoding="utf-8"), malformed)
            self.assertEqual(
                report["summary"][
                    "cc_generic_value_object_cast_action_count"
                ],
                0,
            )

    def test_cc_generic_value_object_casts_fail_on_multiplicity_drift(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._fixture(root, duplicate_boolean_call=True)
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            malformed = (
                "package p;\n"
                "import gnu.trove.f.b.cc;\n"
                "public class A {\n"
                "    public static cc<Boolean> flags = new cc<>();\n"
                "    public static boolean run(Value value) {\n"
                "        A.flags.a(1, (Object)true);\n"
                "        return true;\n"
                "    }\n"
                "}\n"
            )
            source.write_text(malformed, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)

            self.assertEqual(source.read_text(encoding="utf-8"), malformed)
            self.assertEqual(
                report["summary"][
                    "cc_generic_value_object_cast_action_count"
                ],
                0,
            )


class MissingSyntheticConstructorAccessorTests(unittest.TestCase):
    def _fixture(self, root: Path) -> Path:
        legal = root / "synthetic-accessor-legal"
        outer = legal / "p" / "Outer.java"
        marker = legal / "p" / "Marker.java"
        outer.parent.mkdir(parents=True)
        marker.write_text(
            "package p;\n"
            "public final class Marker {}\n",
            encoding="utf-8",
        )
        outer.write_text(
            "package p;\n"
            "public class Outer {\n"
            "    private static class Inner {\n"
            "        private Inner() {}\n"
            "        Inner(Marker ignored) { this(); }\n"
            "    }\n"
            "    private Inner value = new Inner(null);\n"
            "    public Object value() { return value; }\n"
            "}\n",
            encoding="utf-8",
        )
        classes = root / "synthetic-accessor-classes"
        classes.mkdir()
        proc = subprocess.run(
            [
                "javac",
                "-d",
                str(classes),
                str(marker),
                str(outer),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

        nested_path = classes / "p" / "Outer$Inner.class"
        data = bytearray(nested_path.read_bytes())

        def u2_at(offset: int) -> int:
            return struct.unpack_from(">H", data, offset)[0]

        def u4_at(offset: int) -> int:
            return struct.unpack_from(">I", data, offset)[0]

        cp_count = u2_at(8)
        offset = 10
        utf8: dict[int, str] = {}
        index = 1
        while index < cp_count:
            tag = data[offset]
            offset += 1
            if tag == 1:
                length = u2_at(offset)
                offset += 2
                utf8[index] = bytes(
                    data[offset:offset + length]
                ).decode("utf-8")
                offset += length
            elif tag in {3, 4}:
                offset += 4
            elif tag in {5, 6}:
                offset += 8
                index += 1
            elif tag in {7, 8, 16, 19, 20}:
                offset += 2
            elif tag in {9, 10, 11, 12, 17, 18}:
                offset += 4
            elif tag == 15:
                offset += 3
            else:
                raise AssertionError(
                    f"unsupported constant-pool tag {tag}"
                )
            index += 1

        cursor = offset
        cursor += 6
        interfaces_count = u2_at(cursor)
        cursor += 2 + 2 * interfaces_count
        fields_count = u2_at(cursor)
        cursor += 2
        for _ in range(fields_count):
            cursor += 6
            attribute_count = u2_at(cursor)
            cursor += 2
            for _ in range(attribute_count):
                cursor += 2
                length = u4_at(cursor)
                cursor += 4 + length

        methods_count = u2_at(cursor)
        cursor += 2
        patched = 0
        for _ in range(methods_count):
            method_start = cursor
            access = u2_at(cursor)
            name_index = u2_at(cursor + 2)
            descriptor_index = u2_at(cursor + 4)
            attribute_count = u2_at(cursor + 6)
            cursor += 8
            method_name = utf8.get(name_index, "")
            descriptor = utf8.get(descriptor_index, "")
            if (
                method_name == "<init>"
                and descriptor == "(Lp/Marker;)V"
            ):
                struct.pack_into(
                    ">H",
                    data,
                    method_start,
                    access | 0x1000,
                )
                patched += 1
            for _ in range(attribute_count):
                cursor += 2
                length = u4_at(cursor)
                cursor += 4 + length

        self.assertEqual(patched, 1)
        nested_path.write_bytes(bytes(data))

        jar = root / "synthetic-accessor-readable.jar"
        with zipfile.ZipFile(jar, "w") as z:
            for class_file in sorted(classes.rglob("*.class")):
                z.write(
                    class_file,
                    class_file.relative_to(classes).as_posix(),
                )

        with zipfile.ZipFile(jar) as z:
            nested = profile_class_field_accesses_exact(
                z.read("p/Outer$Inner.class")
            )
        synthetic = [
            method
            for method in nested["methods"]
            if method["name"] == "<init>"
            and int(method["access"]) & 0x1000
        ]
        self.assertEqual(len(synthetic), 1)
        self.assertEqual(
            synthetic[0]["descriptor"],
            "(Lp/Marker;)V",
        )
        self.assertEqual(
            synthetic[0]["instructions"][0]["mnemonic"],
            "aload",
        )
        self.assertEqual(
            synthetic[0]["instructions"][0]["local_index"],
            0,
        )
        self.assertEqual(
            synthetic[0]["instructions"][1]["mnemonic"],
            "invokespecial",
        )
        self.assertEqual(
            synthetic[0]["instructions"][2]["mnemonic"],
            "return",
        )
        return jar

    def _malformed_source(self, *, duplicate_call: bool = False) -> str:
        second = (
            "    private Inner value2 = new Inner(null);\n"
            if duplicate_call
            else ""
        )
        return (
            "package p;\n"
            "public class Outer {\n"
            "    private static class Inner {\n"
            "        private Inner() {}\n"
            "    }\n"
            "    private Inner value = new Inner(null);\n"
            + second
            + "    public Object value() { return value; }\n"
            "}\n"
        )

    def _patch_synthetic_constructor_opcode(
        self,
        jar: Path,
        *,
        instruction_index: int,
        opcode: int,
    ) -> Path:
        with zipfile.ZipFile(jar) as z:
            entries = {
                info.filename: z.read(info.filename)
                for info in z.infolist()
            }

        name = "p/Outer$Inner.class"
        data = bytearray(entries[name])

        def u2_at(offset: int) -> int:
            return struct.unpack_from(">H", data, offset)[0]

        def u4_at(offset: int) -> int:
            return struct.unpack_from(">I", data, offset)[0]

        cp_count = u2_at(8)
        offset = 10
        utf8: dict[int, str] = {}
        index = 1
        while index < cp_count:
            tag = data[offset]
            offset += 1
            if tag == 1:
                length = u2_at(offset)
                offset += 2
                utf8[index] = bytes(
                    data[offset:offset + length]
                ).decode("utf-8")
                offset += length
            elif tag in {3, 4}:
                offset += 4
            elif tag in {5, 6}:
                offset += 8
                index += 1
            elif tag in {7, 8, 16, 19, 20}:
                offset += 2
            elif tag in {9, 10, 11, 12, 17, 18}:
                offset += 4
            elif tag == 15:
                offset += 3
            else:
                raise AssertionError(
                    f"unsupported constant-pool tag {tag}"
                )
            index += 1

        cursor = offset
        cursor += 6
        interfaces_count = u2_at(cursor)
        cursor += 2 + 2 * interfaces_count

        fields_count = u2_at(cursor)
        cursor += 2
        for _ in range(fields_count):
            cursor += 6
            attribute_count = u2_at(cursor)
            cursor += 2
            for _ in range(attribute_count):
                cursor += 2
                length = u4_at(cursor)
                cursor += 4 + length

        methods_count = u2_at(cursor)
        cursor += 2
        patched = 0
        for _ in range(methods_count):
            access = u2_at(cursor)
            name_index = u2_at(cursor + 2)
            descriptor_index = u2_at(cursor + 4)
            attribute_count = u2_at(cursor + 6)
            cursor += 8
            method_name = utf8.get(name_index, "")
            descriptor = utf8.get(descriptor_index, "")

            for _ in range(attribute_count):
                attr_name_index = u2_at(cursor)
                length = u4_at(cursor + 2)
                payload = cursor + 6
                if (
                    method_name == "<init>"
                    and descriptor != "()V"
                    and (access & 0x1000)
                    and utf8.get(attr_name_index) == "Code"
                ):
                    code_length = u4_at(payload + 4)
                    code_start = payload + 8
                    profile = profile_class_field_accesses_exact(
                        bytes(data)
                    )
                    method = next(
                        row
                        for row in profile["methods"]
                        if row["name"] == "<init>"
                        and row["descriptor"] == descriptor
                    )
                    instructions = method["instructions"]
                    self.assertGreater(
                        len(instructions),
                        instruction_index,
                    )
                    target_offset = int(
                        instructions[instruction_index]["offset"]
                    )
                    self.assertLess(target_offset, code_length)
                    data[code_start + target_offset] = opcode
                    patched += 1
                cursor = payload + length

        self.assertEqual(patched, 1)
        entries[name] = bytes(data)
        out = jar.with_name(
            jar.stem
            + f"-patched-{instruction_index}-{opcode:02x}.jar"
        )
        with zipfile.ZipFile(out, "w") as z:
            for entry_name, payload in sorted(entries.items()):
                z.writestr(entry_name, payload)
        return out

    def test_reconstructs_omitted_synthetic_constructor_accessor(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._fixture(root)
            source = root / "src" / "p" / "Outer.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                self._malformed_source(),
                encoding="utf-8",
            )

            before = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "before-synthetic-accessor"),
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
                "Inner(final p.Marker recoveredSyntheticAccessor)",
                normalized,
            )
            self.assertIn("this();", normalized)

            action = next(
                row
                for row in report["actions"]
                if row["kind"]
                == "missing_synthetic_constructor_accessor_reconstruction"
            )
            self.assertEqual(action["nested_owner"], "p/Outer$Inner")
            self.assertEqual(action["source_callsite_count"], 1)
            self.assertEqual(action["replacement_count"], 1)
            self.assertEqual(
                report["summary"][
                    "missing_synthetic_constructor_accessor_action_count"
                ],
                1,
            )
            self.assertEqual(
                report["summary"][
                    "missing_synthetic_constructor_accessor_method_count"
                ],
                1,
            )

            after = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "after-synthetic-accessor"),
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

    def test_synthetic_constructor_accessor_fails_on_dummy_use(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._fixture(root)
            drift = self._patch_synthetic_constructor_opcode(
                jar,
                instruction_index=0,
                opcode=0x2B,
            )
            source = root / "src" / "p" / "Outer.java"
            source.parent.mkdir(parents=True)
            malformed = self._malformed_source()
            source.write_text(malformed, encoding="utf-8")

            report = normalize_procyon_source(root / "src", drift)
            self.assertEqual(source.read_text(encoding="utf-8"), malformed)
            self.assertEqual(
                report["summary"][
                    "missing_synthetic_constructor_accessor_action_count"
                ],
                0,
            )

    def test_synthetic_constructor_accessor_fails_on_body_drift(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._fixture(root)
            drift = self._patch_synthetic_constructor_opcode(
                jar,
                instruction_index=1,
                opcode=0xB6,
            )
            source = root / "src" / "p" / "Outer.java"
            source.parent.mkdir(parents=True)
            malformed = self._malformed_source()
            source.write_text(malformed, encoding="utf-8")

            report = normalize_procyon_source(root / "src", drift)
            self.assertEqual(source.read_text(encoding="utf-8"), malformed)
            self.assertEqual(
                report["summary"][
                    "missing_synthetic_constructor_accessor_action_count"
                ],
                0,
            )

    def test_synthetic_constructor_accessor_fails_on_callsite_multiplicity(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._fixture(root)
            source = root / "src" / "p" / "Outer.java"
            source.parent.mkdir(parents=True)
            malformed = self._malformed_source(duplicate_call=True)
            source.write_text(malformed, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)
            self.assertEqual(source.read_text(encoding="utf-8"), malformed)
            self.assertEqual(
                report["summary"][
                    "missing_synthetic_constructor_accessor_action_count"
                ],
                0,
            )





class ErasedMapMixedObjectLocalTests(unittest.TestCase):
    def _fixture(
        self,
        root: Path,
        *,
        mode: str = "mixed",
    ) -> Path:
        if mode == "mixed":
            body = (
                "        Object value = map.get(key);\n"
                "        if (value instanceof Integer) {\n"
                "            return ((Integer)value).intValue();\n"
                "        }\n"
                "        if (value instanceof String) {\n"
                "            return ((String)value).length();\n"
                "        }\n"
                "        return 0;\n"
            )
        elif mode == "single":
            body = (
                "        Object value = map.get(key);\n"
                "        if (value instanceof Integer) {\n"
                "            return ((Integer)value).intValue();\n"
                "        }\n"
                "        return 0;\n"
            )
        elif mode == "immediate":
            body = (
                "        Integer value = (Integer)map.get(key);\n"
                "        return value.intValue();\n"
            )
        elif mode == "double":
            body = (
                "        Object value = map.get(key);\n"
                "        if (value instanceof Integer) {\n"
                "            ((Integer)value).intValue();\n"
                "        }\n"
                "        if (value instanceof String) {\n"
                "            ((String)value).length();\n"
                "        }\n"
                "        Object other = map.get(otherKey);\n"
                "        if (other instanceof Integer) {\n"
                "            ((Integer)other).intValue();\n"
                "        }\n"
                "        if (other instanceof String) {\n"
                "            ((String)other).length();\n"
                "        }\n"
                "        return 0;\n"
            )
        else:
            raise AssertionError(mode)

        return _compile_java_fixture(
            root,
            {
                "p/A.java": (
                    "package p;\n"
                    "import java.util.Map;\n"
                    "public class A {\n"
                    "    public static int read("
                    "Map<String, Object> map, String key, "
                    "String otherKey) {\n"
                    + body
                    + "    }\n"
                    "}\n"
                ),
            },
        )

    def _malformed_source(self) -> str:
        return (
            "package p;\n"
            "import java.util.Map;\n"
            "public class A {\n"
            "    public static int read("
            "Map<String, Object> map, String key, "
            "String otherKey) {\n"
            "        final Integer value = map.get(key);\n"
            "        if (value instanceof Integer) {\n"
            "            return ((Integer)value).intValue();\n"
            "        }\n"
            "        if (((String)value).isEmpty()) {\n"
            "            return 1;\n"
            "        }\n"
            "        return ((String)value).length();\n"
            "    }\n"
            "}\n"
        )

    def test_mixed_map_get_local_restores_object_declaration(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._fixture(root)
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                self._malformed_source(),
                encoding="utf-8",
            )

            before = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "before-mixed-map-local"),
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
                "final Object value = map.get(key);",
                normalized,
            )
            action = next(
                row
                for row in report["actions"]
                if row["kind"]
                == "erased_map_mixed_object_local_reconstruction"
            )
            self.assertEqual(action["replacement_count"], 1)
            self.assertEqual(action["local_names"], ["value"])
            self.assertEqual(
                set(action["flows"][0]["checkcast_types"]),
                {"java/lang/Integer", "java/lang/String"},
            )
            self.assertEqual(
                report["summary"][
                    "erased_map_mixed_object_local_action_count"
                ],
                1,
            )
            self.assertEqual(
                report["summary"][
                    "erased_map_mixed_object_local_reference_count"
                ],
                1,
            )

            after = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "after-mixed-map-local"),
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

    def test_mixed_map_get_local_fails_on_single_type_lifetime(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._fixture(root, mode="single")
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            malformed = self._malformed_source()
            source.write_text(malformed, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)
            self.assertEqual(source.read_text(encoding="utf-8"), malformed)
            self.assertEqual(
                report["summary"][
                    "erased_map_mixed_object_local_action_count"
                ],
                0,
            )

    def test_mixed_map_get_local_fails_on_immediate_checkcast(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._fixture(root, mode="immediate")
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            malformed = self._malformed_source()
            source.write_text(malformed, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)
            self.assertEqual(source.read_text(encoding="utf-8"), malformed)
            self.assertEqual(
                report["summary"][
                    "erased_map_mixed_object_local_action_count"
                ],
                0,
            )

    def test_mixed_map_get_local_fails_on_exact_multiplicity_drift(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._fixture(root, mode="double")
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            malformed = self._malformed_source()
            source.write_text(malformed, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)
            self.assertEqual(source.read_text(encoding="utf-8"), malformed)
            self.assertEqual(
                report["summary"][
                    "erased_map_mixed_object_local_action_count"
                ],
                0,
            )




class MethodHandleInvokeExactResultCastTests(unittest.TestCase):
    def _fixture(
        self,
        root: Path,
        *,
        mode: str = "consumer",
        duplicate: bool = False,
    ) -> Path:
        if mode == "consumer":
            target = "Consumer<Object>"
            cast = "(Consumer<Object>)"
        elif mode == "string":
            target = "String"
            cast = "(String)"
        elif mode == "object":
            target = "Object"
            cast = "(Object)"
        else:
            raise AssertionError(mode)

        second = (
            "        " + target + " other;\n"
            "        other = " + cast
            + "(handle.invokeExact());\n"
            if duplicate
            else ""
        )
        return _compile_java_fixture(
            root,
            {
                "p/A.java": (
                    "package p;\n"
                    "import java.lang.invoke.MethodHandle;\n"
                    "import java.util.function.Consumer;\n"
                    "public class A {\n"
                    "    public static Object read(MethodHandle handle) "
                    "throws Throwable {\n"
                    "        " + target + " value;\n"
                    "        value = " + cast
                    + "(handle.invokeExact());\n"
                    + second
                    + "        return value;\n"
                    "    }\n"
                    "}\n"
                ),
            },
        )

    def _malformed_source(
        self,
        *,
        target: str = "Consumer<Object>",
    ) -> str:
        return (
            "package p;\n"
            "import java.lang.invoke.MethodHandle;\n"
            "import java.util.function.Consumer;\n"
            "public class A {\n"
            "    public static Object read(MethodHandle handle) "
            "throws Throwable {\n"
            "        " + target + " value;\n"
            "        value = handle.invokeExact();\n"
            "        return value;\n"
            "    }\n"
            "}\n"
        )

    def test_invokeexact_result_cast_restores_exact_target_type(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._fixture(root)
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            source.write_text(
                self._malformed_source(),
                encoding="utf-8",
            )

            before = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "before-invokeexact-result"),
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
                "Consumer<Object> value;",
                normalized,
            )
            self.assertIn(
                "value = (Consumer<Object>)(handle.invokeExact());",
                normalized,
            )
            action = next(
                row
                for row in report["actions"]
                if row["kind"]
                == "methodhandle_invokeexact_result_cast_reconstruction"
            )
            self.assertEqual(action["replacement_count"], 1)
            self.assertEqual(action["local_names"], ["value"])
            self.assertEqual(
                action["flows"][0]["return_descriptor"],
                "Ljava/util/function/Consumer;",
            )
            self.assertEqual(
                report["summary"][
                    "methodhandle_invokeexact_result_cast_action_count"
                ],
                1,
            )
            self.assertEqual(
                report["summary"][
                    "methodhandle_invokeexact_result_cast_reference_count"
                ],
                1,
            )

            after = subprocess.run(
                [
                    "javac",
                    "-cp",
                    str(jar),
                    "-d",
                    str(root / "after-invokeexact-result"),
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

    def test_invokeexact_result_cast_fails_on_target_type_drift(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._fixture(root, mode="string")
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            malformed = self._malformed_source()
            source.write_text(malformed, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)
            self.assertEqual(source.read_text(encoding="utf-8"), malformed)
            self.assertEqual(
                report["summary"][
                    "methodhandle_invokeexact_result_cast_action_count"
                ],
                0,
            )

    def test_invokeexact_result_cast_fails_on_object_return_descriptor(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._fixture(root, mode="object")
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            malformed = self._malformed_source(target="Object")
            source.write_text(malformed, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)
            self.assertEqual(source.read_text(encoding="utf-8"), malformed)
            self.assertEqual(
                report["summary"][
                    "methodhandle_invokeexact_result_cast_action_count"
                ],
                0,
            )

    def test_invokeexact_result_cast_fails_on_same_simple_name_type_collision(
        self,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = _compile_java_fixture(
                root,
                {
                    "p/Consumer.java": (
                        "package p;\n"
                        "public class Consumer {}\n"
                    ),
                    "p/A.java": (
                        "package p;\n"
                        "import java.lang.invoke.MethodHandle;\n"
                        "public class A {\n"
                        "    public static Object read(MethodHandle handle) "
                        "throws Throwable {\n"
                        "        java.util.function.Consumer<Object> value;\n"
                        "        value = (java.util.function.Consumer<Object>)"
                        "(handle.invokeExact());\n"
                        "        return value;\n"
                        "    }\n"
                        "}\n"
                    ),
                },
            )
            source_root = root / "src"
            source = source_root / "p" / "A.java"
            local_consumer = source_root / "p" / "Consumer.java"
            source.parent.mkdir(parents=True)
            original = (
                "package p;\n"
                "import java.lang.invoke.MethodHandle;\n"
                "public class A {\n"
                "    public static Object read(MethodHandle handle) "
                "throws Throwable {\n"
                "        Consumer value;\n"
                "        value = handle.invokeExact();\n"
                "        return value;\n"
                "    }\n"
                "}\n"
            )
            source.write_text(original, encoding="utf-8")
            local_consumer.write_text(
                "package p;\n"
                "public class Consumer {}\n",
                encoding="utf-8",
            )

            report = normalize_procyon_source(source_root, jar)

            self.assertEqual(source.read_text(encoding="utf-8"), original)
            self.assertEqual(
                report["summary"][
                    "methodhandle_invokeexact_result_cast_action_count"
                ],
                0,
            )

    def test_invokeexact_result_cast_fails_on_multiplicity_drift(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            jar = self._fixture(root, duplicate=True)
            source = root / "src" / "p" / "A.java"
            source.parent.mkdir(parents=True)
            malformed = self._malformed_source()
            source.write_text(malformed, encoding="utf-8")

            report = normalize_procyon_source(root / "src", jar)
            self.assertEqual(source.read_text(encoding="utf-8"), malformed)
            self.assertEqual(
                report["summary"][
                    "methodhandle_invokeexact_result_cast_action_count"
                ],
                0,
            )




if __name__ == "__main__":
    unittest.main()

# R8M exact-v308 acceptance is recorded on PR #114; keep this test surface CI-bound.

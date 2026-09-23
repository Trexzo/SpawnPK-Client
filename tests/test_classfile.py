import struct
import unittest

from spk_recovery.classfile import _descriptor_shape, parse_class


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


def _minimal_nested_class_bytes(*, include_inner_classes: bool) -> bytes:
    # Constant pool:
    # 1 Outer$Inner, 2 Class#1, 3 java/lang/Object, 4 Class#3,
    # 5 InnerClasses, 6 Outer, 7 Class#6, 8 Inner.
    cp = [
        _utf8("Outer$Inner"),
        _class(1),
        _utf8("java/lang/Object"),
        _class(3),
        _utf8("InnerClasses"),
        _utf8("Outer"),
        _class(6),
        _utf8("Inner"),
    ]
    out = bytearray()
    out += _u4(0xCAFEBABE)
    out += _u2(0)
    out += _u2(52)
    out += _u2(len(cp) + 1)
    for entry in cp:
        out += entry
    out += _u2(0x0021)  # ACC_PUBLIC | ACC_SUPER
    out += _u2(2)       # this_class
    out += _u2(4)       # super_class
    out += _u2(0)       # interfaces_count
    out += _u2(0)       # fields_count
    out += _u2(0)       # methods_count
    if include_inner_classes:
        payload = (
            _u2(1)      # number_of_classes
            + _u2(2)    # inner_class_info_index
            + _u2(7)    # outer_class_info_index
            + _u2(8)    # inner_name_index
            + _u2(0x0001)
        )
        out += _u2(1)
        out += _u2(5)
        out += _u4(len(payload))
        out += payload
    else:
        out += _u2(0)
    return bytes(out)


def _minimal_enclosing_class_bytes() -> bytes:
    # Constant pool:
    # 1 Outer$1, 2 Class#1, 3 java/lang/Object, 4 Class#3,
    # 5 EnclosingMethod, 6 Outer, 7 Class#6.
    cp = [
        _utf8("Outer$1"),
        _class(1),
        _utf8("java/lang/Object"),
        _class(3),
        _utf8("EnclosingMethod"),
        _utf8("Outer"),
        _class(6),
    ]
    out = bytearray()
    out += _u4(0xCAFEBABE)
    out += _u2(0)
    out += _u2(52)
    out += _u2(len(cp) + 1)
    for entry in cp:
        out += entry
    out += _u2(0x0021)
    out += _u2(2)
    out += _u2(4)
    out += _u2(0)
    out += _u2(0)
    out += _u2(0)
    payload = _u2(7) + _u2(0)
    out += _u2(1)
    out += _u2(5)
    out += _u4(len(payload))
    out += payload
    return bytes(out)


class DescriptorShapeTests(unittest.TestCase):
    def test_descriptor_shape_removes_reference_names(self):
        self.assertEqual(
            _descriptor_shape("(Lrs/a;I[Ljava/lang/String;)Lrs/b;"),
            "(L;I[L;)L;",
        )


class NestingMetadataTests(unittest.TestCase):
    def test_inner_classes_attribute_exposes_outer_owner(self):
        parsed = parse_class(
            _minimal_nested_class_bytes(include_inner_classes=True)
        )
        self.assertEqual(parsed.name, "Outer$Inner")
        self.assertEqual(parsed.inner_outer_name, "Outer")
        self.assertIsNone(parsed.enclosing_class_name)


    def test_enclosing_method_attribute_exposes_enclosing_class(self):
        parsed = parse_class(_minimal_enclosing_class_bytes())
        self.assertEqual(parsed.name, "Outer$1")
        self.assertIsNone(parsed.inner_outer_name)
        self.assertEqual(parsed.enclosing_class_name, "Outer")

    def test_dollar_name_without_attribute_is_not_nesting_evidence(self):
        parsed = parse_class(
            _minimal_nested_class_bytes(include_inner_classes=False)
        )
        self.assertEqual(parsed.name, "Outer$Inner")
        self.assertIsNone(parsed.inner_outer_name)
        self.assertIsNone(parsed.enclosing_class_name)


if __name__ == "__main__":
    unittest.main()

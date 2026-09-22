import unittest

from spk_recovery.classfile import _descriptor_shape


class DescriptorShapeTests(unittest.TestCase):
    def test_descriptor_shape_removes_reference_names(self):
        self.assertEqual(
            _descriptor_shape("(Lrs/a;I[Ljava/lang/String;)Lrs/b;"),
            "(L;I[L;)L;",
        )


if __name__ == "__main__":
    unittest.main()

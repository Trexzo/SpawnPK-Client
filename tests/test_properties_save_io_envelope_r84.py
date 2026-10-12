"""R84: original save I/O preamble and epilogue cannot silently drift."""
import unittest
from spk_recovery.properties_save_io_envelope import OPEN, TAIL, _join, call
from spk_recovery.properties_save_writer_source import SaveWriterSourceError

class SaveFileEnvelopeTests(unittest.TestCase):
    def test_original_jvm_op_shapes_have_exact_bounded_lengths(self):
        self.assertEqual(len(OPEN),20)
        self.assertEqual(len(TAIL),28)
        self.assertEqual(OPEN[:6],("0xbb","0x59","0xb2","0xba","0xb7","0x4b"))
        self.assertEqual(TAIL[-5:],("0xa7","0x4b","0x2a","0xb6","0xb1"))
        self.assertEqual(TAIL.count("0xb8"),4)

    def test_concat_exact_dynamic_slot_count(self):
        self.assertEqual(_join(["pre","post"],["field"]),'"pre" + field + "post"')
        self.assertEqual(_join(["", ""],["field"]),"field")
        with self.assertRaisesRegex(SaveWriterSourceError,"DYNAMIC_ARGUMENT_COUNT"):
            _join(["wrong"],["field"])

    def test_io_call_strict_owner_and_descriptor(self):
        good={"opcode":"0xb8","owner":"java/nio/file/Files","name":"delete",
              "descriptor":"(Ljava/nio/file/Path;)V"}
        self.assertTrue(call(good,"0xb8","java/nio/file/Files","delete",
                             "(Ljava/nio/file/Path;)V"))
        self.assertFalse(call(good,"0xb8","java/nio/file/Files","copy",
                              "(Ljava/nio/file/Path;)V"))
        self.assertFalse(call(good,"0xb8","java/nio/file/Files","delete",
                              "(Ljava/lang/String;)V"))

if __name__=="__main__":
    unittest.main()

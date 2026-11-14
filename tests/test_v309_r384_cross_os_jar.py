"""R384 public synthetic tests: archive headers, no proprietary source required."""
from __future__ import annotations
import hashlib
import importlib.util
import io
import struct
import sys
import unittest
import zipfile
from pathlib import Path

RUNNER = Path(__file__).resolve().parents[1] / 'tools/r383/verify_private_full_build.py'
spec = importlib.util.spec_from_file_location('r384_jar_runner', RUNNER)
r = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = r
spec.loader.exec_module(r)


def one_class_jar(creator: int | None) -> bytes:
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, 'w') as z:
        if creator is None:
            entry = r.canonical_class_zipinfo('rs/Test.class')
        else:
            entry = zipfile.ZipInfo('rs/Test.class', (2026, 10, 18, 0, 0, 0))
            entry.create_system = creator
            entry.external_attr = 0o644 << 16
            entry.compress_type = zipfile.ZIP_DEFLATED
        z.writestr(entry, bytes.fromhex('CAFEBABE')+b'synthetic', compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return bio.getvalue()


class CrossOSJarTests(unittest.TestCase):
    def test_zip_creator_is_host_dependent_without_override(self):
        self.assertNotEqual(hashlib.sha256(one_class_jar(0)).digest(), hashlib.sha256(one_class_jar(3)).digest())

    def test_canonical_bytes_match_linux_baseline(self):
        self.assertEqual(one_class_jar(None), one_class_jar(3))

    def test_canonical_creator_header_is_unix_on_both_hosts(self):
        data = one_class_jar(None)
        central = data.index(b'PK\x01\x02')
        version_made_by = struct.unpack_from('<H', data, central+4)[0]
        self.assertEqual(version_made_by >> 8, 3)

    def test_archive_roundtrip_preserves_class_content(self):
        with zipfile.ZipFile(io.BytesIO(one_class_jar(None))) as z:
            self.assertEqual(z.namelist(), ['rs/Test.class'])
            self.assertEqual(z.read('rs/Test.class'), bytes.fromhex('CAFEBABE')+b'synthetic')

    def test_archive_metadata_is_pinned(self):
        with zipfile.ZipFile(io.BytesIO(one_class_jar(None))) as z:
            info = z.infolist()[0]
            self.assertEqual(info.date_time, (2026, 10, 18, 0, 0, 0))
            self.assertEqual(info.external_attr, 0o644 << 16)
            self.assertEqual(info.create_system, 3)

    def test_bad_relative_class_path_refused(self):
        for path in ('../A.class', '/A.class', 'A.java', 'a//B.class', 'a\\B.class'):
            with self.subTest(path=path), self.assertRaises(r.Refused):
                r.canonical_class_zipinfo(path)

if __name__ == '__main__': unittest.main(verbosity=2)

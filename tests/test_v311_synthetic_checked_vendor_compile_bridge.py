"""Synthetic JDK9-only checked vendor exception metadata compatibility tests.

All Java types are invented toy fixtures; no original game or vendor code.
"""
import struct
import subprocess
import tempfile
import unittest
import zipfile
import shutil
from pathlib import Path


def call(args, ok=True):
    proc = subprocess.run(args, capture_output=True, text=True, timeout=50)
    if ok and proc.returncode:
        raise AssertionError(proc.stderr[-1200:])
    return proc


def add_checked_exception(data, method, descriptor):
    """Add compile-only Exceptions metadata to ONE real compiled toy vendor method."""
    if data[:4] != bytes.fromhex("cafebabe"):
        raise ValueError("NOT_A_VENDOR_CLASS")
    u2 = lambda b, p: struct.unpack_from(">H", b, p)[0]
    u4 = lambda b, p: struct.unpack_from(">I", b, p)[0]
    count = u2(data, 8)
    words = {}
    off = 10
    j = 1
    while j < count:
        tag = data[off]
        off += 1
        if tag == 1:
            n = u2(data, off)
            off += 2
            words[j] = data[off:off + n].decode("utf-8")
            off += n
        elif tag in (3, 4):
            off += 4
        elif tag in (5, 6):
            off += 8
            j += 1
        elif tag in (7, 8, 16, 19, 20):
            off += 2
        elif tag in (9, 10, 11, 12, 17, 18):
            off += 4
        elif tag == 15:
            off += 3
        else:
            raise ValueError("UNKNOWN_CONSTANT_POOL_TAG")
        j += 1
    cp_end = off
    extra = b""
    for name in ("Exceptions", "java/io/IOException"):
        value = name.encode("utf-8")
        extra += b"\x01" + struct.pack(">H", len(value)) + value
    extra += b"\x07" + struct.pack(">H", count + 1)
    tail = bytearray(data[cp_end:])
    pos = 6
    pos += 2 + 2 * u2(tail, pos)

    def end_member(p):
        q = p + 8
        for _ in range(u2(tail, p + 6)):
            q += 6 + u4(tail, q + 2)
        return q

    fields = u2(tail, pos)
    pos += 2
    for _ in range(fields):
        pos = end_member(pos)
    methods = u2(tail, pos)
    pos += 2
    found = 0
    for _ in range(methods):
        name = words[u2(tail, pos + 2)]
        desc = words[u2(tail, pos + 4)]
        end = end_member(pos)
        if (name, desc) == (method, descriptor):
            found += 1
            struct.pack_into(">H", tail, pos + 6, u2(tail, pos + 6) + 1)
            addition = struct.pack(">HIHH", count, 4, 1, count + 2)
            tail[end:end] = addition
            end += len(addition)
        pos = end
    if found != 1:
        raise ValueError("EXACT_VENDOR_METHOD_NOT_FOUND")
    return data[:8] + struct.pack(">H", count + 3) + data[10:cp_end] + extra + tail


@unittest.skipUnless(all(shutil.which(x) for x in ("javac", "javap", "java")),
                     "JDK9+ required")
class ToyCheckedVendorBridge(unittest.TestCase):
    def test_vendor_binary_only_exception_declaration_does_not_modify_code(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            vendor = root / "ToyVendor.java"
            vendor.write_text(
                "public class ToyVendor { "
                "public static String text(java.lang.Readable r){return r.toString();}}"
            )
            call(["javac", "--release", "9", "-g:none", "-d", str(root), str(vendor)])
            binary = (root / "ToyVendor.class").read_bytes()
            original = root / "vendor-original.jar"
            patched = root / "vendor-compile-only.jar"
            with zipfile.ZipFile(original, "w") as z:
                z.writestr("ToyVendor.class", binary)
            with zipfile.ZipFile(patched, "w") as z:
                z.writestr("ToyVendor.class", add_checked_exception(
                    binary, "text", "(Ljava/lang/Readable;)Ljava/lang/String;"))
            owner = root / "ToyOwner.java"
            owner.write_text(
                "public class ToyOwner {public String read(java.lang.Readable r){"
                "try{return ToyVendor.text(r);}catch(java.io.IOException x){"
                "throw new IllegalStateException(x);}}}"
            )
            out = root / "game"
            out.mkdir()
            refused = call(["javac", "--release", "9", "-proc:none",
                            "-classpath", str(original), "-d", str(out),
                            str(owner)], ok=False)
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn("IOException", refused.stderr)
            call(["javac", "--release", "9", "-proc:none", "-g:none",
                  "-classpath", str(patched), "-d", str(out), str(owner)])
            before = call(["javap", "-c", "-p", "-classpath", str(original),
                           "ToyVendor"]).stdout
            after = call(["javap", "-c", "-p", "-classpath", str(patched),
                          "ToyVendor"]).stdout
            self.assertEqual(before, after.replace(" throws java.io.IOException", ""))
            probe = root / "ToyProbe.java"
            probe.write_text(
                "public class ToyProbe {public static void main(String[] a){"
                "System.out.println(new ToyOwner().read("
                "java.nio.CharBuffer.wrap(\"toy resource\")));}}"
            )
            call(["javac", "--release", "9", "-classpath",
                  str(out) + __import__("os").pathsep + str(original),
                  "-d", str(root), str(probe)])
            for jar in (original, patched):
                transcript = call(["java", "-cp",
                    str(root) + __import__("os").pathsep + str(out)
                    + __import__("os").pathsep + str(jar), "ToyProbe"]).stdout
                self.assertEqual(transcript, "toy resource\n")

    def test_tampered_vendor_class_or_unrecognized_method_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "NOT_A_VENDOR_CLASS"):
            add_checked_exception(b"not compiled", "x", "()V")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            p = root / "Foo.java"
            p.write_text("public class Foo {public void ok(){}}")
            call(["javac", "--release", "9", "-d", temp, str(p)])
            with self.assertRaisesRegex(ValueError, "EXACT_VENDOR_METHOD_NOT_FOUND"):
                add_checked_exception((root / "Foo.class").read_bytes(), "bad", "()V")


if __name__ == "__main__":
    unittest.main(verbosity=2)

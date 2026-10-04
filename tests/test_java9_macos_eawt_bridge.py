from __future__ import annotations

from pathlib import Path
import shutil
import tempfile
import unittest

from spk_recovery.classfile import parse_class
from spk_recovery.java9_macos_eawt_bridge import (
    Java9MacosEawtBridgeError,
    V308_AUTHORITY,
    bridge_id,
    build_java9_macos_eawt_compile_bridge,
)


@unittest.skipUnless(shutil.which("javac"), "javac required")
class Java9MacosEawtBridgeTests(unittest.TestCase):
    def test_bridge_is_exact_java9_compile_only_surface(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            classes, report = (
                build_java9_macos_eawt_compile_bridge(
                    root / "bridge",
                    javac_command="javac",
                    release=9,
                )
            )

            self.assertEqual(
                report["bridge_id"],
                bridge_id(),
            )
            self.assertEqual(report["target_release"], 9)
            self.assertEqual(report["class_count"], 5)
            self.assertEqual(report["source_count"], 5)
            self.assertFalse(report["runtime_allowed"])
            self.assertEqual(
                report["authority"]["classfile_major"],
                53,
            )
            self.assertEqual(
                report["authority"]["project_classes"],
                V308_AUTHORITY["project_classes"],
            )

            adapter = parse_class(
                (
                    classes
                    / "com/apple/eawt/FullScreenAdapter.class"
                ).read_bytes()
            )
            self.assertEqual(adapter.major, 53)
            self.assertEqual(
                adapter.interfaces,
                ["com/apple/eawt/FullScreenListener"],
            )

            event = parse_class(
                (
                    classes
                    / "com/apple/eawt/event/FullScreenEvent.class"
                ).read_bytes()
            )
            self.assertEqual(
                event.super_name,
                "java/util/EventObject",
            )

    def test_bridge_refuses_non_java9_release(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(
                Java9MacosEawtBridgeError,
                "requires target release 9",
            ):
                build_java9_macos_eawt_compile_bridge(
                    Path(td) / "bridge",
                    javac_command="javac",
                    release=8,
                )


if __name__ == "__main__":
    unittest.main()

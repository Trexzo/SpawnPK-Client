"""R393 synthetic-only plugin-startup risk inventory regression checks."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import stat
import tempfile
import unittest
import warnings
import zipfile

SCRIPT = Path(__file__).resolve().parents[1] / "tools/r393/audit_plugin_startup.py"
spec = importlib.util.spec_from_file_location("r393_plugin_audit", SCRIPT)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.kit = self.root / "private_synthetic_kit.zip"
        self.files = {
            "source/rs/pkg42/Class255.java":
                b"public class Class255 { void method(){ loadPlugins(); startPlugins(); } }",
            "source/rs/plugins/PluginManager.java":
                b"public class PluginManager { void go(){ SwingUtilities.invokeAndWait(task); p.startUp(); } }",
            "source/rs/plugins/loadouts/LoadoutsPlugin.java":
                b"public class LoadoutsPlugin extends Plugin { "
                b"protected void startUp(){ new LoadoutsPanel(); } }",
            "source/rs/gui/loadouts/LoadoutsPanel.java":
                b"public class LoadoutsPanel { public LoadoutsPanel(){"
                b"  try{new File(path).delete();}catch(Exception e){}"
                b"  Files.write(path, data); loadFolder();"
                b"} }",
            "source/rs/plugins/loottracker/LootTrackerPlugin.java":
                b"public class LootTrackerPlugin extends Plugin {"
                b"protected void startUp(){ history.deleteStale(); } }",
            "source/rs/plugins/profiles/ProfilesPlugin.java":
                b"public class ProfilesPlugin extends Plugin {"
                b"protected void startUp(){ new ProfileRegistry(); } }",
            "source/rs/plugins/profiles/ProfileRegistry.java":
                b"class ProfileRegistry { ProfileRegistry(){store.load();} }",
            "source/rs/plugins/marketsnipe/MarketSnipePlugin.java":
                b"public class MarketSnipePlugin extends Plugin {"
                b"protected void startUp(){ blacklist.seedDefaultsIfEmpty(); } }",
        }
        self.pack()

    def pack(self, items=None):
        if items is None:
            items = list(self.files.items())
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(self.kit, "w") as f:
                for name, value in items:
                    f.writestr(name, value)

    def digest(self):
        return hashlib.sha256(self.kit.read_bytes()).hexdigest()

    def scan(self):
        audit.pinned_archive(self.kit, self.digest())
        sources = audit.load_sources(self.kit, len(self.files))
        return audit.audit_sources(sources)

    def test_real_startup_indicators_are_distinguished(self):
        result = self.scan()
        self.assertEqual(result["plugin_subclass_count"], 4)
        self.assertEqual(result["startup_override_count"], 4)
        details = result["per_plugin_evidence"]
        self.assertEqual(details["LootTrackerPlugin"]["direct_indicators"], ["cleanup"])
        self.assertIn("cleanup", details["LoadoutsPlugin"]["one_hop_constructor_indicators"])
        self.assertIn("write", details["LoadoutsPlugin"]["one_hop_constructor_indicators"])
        self.assertIn("read", details["ProfilesPlugin"]["one_hop_constructor_indicators"])
        self.assertIn("write", details["MarketSnipePlugin"]["direct_indicators"])

    def test_always_fail_closed(self):
        result = self.scan()
        for key in ("client_executed", "runtime_plugin_startup_executed",
                    "freeze_root_cause_proven", "isolation_verified",
                    "launch_authorized", "plugin_enablement_verified",
                    "source_release_approved"):
            self.assertFalse(result[key])

    def test_no_source_bodies_or_file_paths_in_report(self):
        report = json.dumps(self.scan())
        self.assertNotIn("Files.write(", report)
        self.assertNotIn("source/rs/", report)
        self.assertNotIn("new File(", report)

    def test_java_comment_not_counted(self):
        self.files["source/rs/plugins/loottracker/LootTrackerPlugin.java"] = (
            b"public class LootTrackerPlugin extends Plugin { "
            b"protected void startUp(){ // history.deleteStale();\n"
            b' String example = "Files.deleteIfExists(path);";'
            b" /* new ProcessBuilder(); */"
            b" } }")
        self.pack()
        result = self.scan()
        self.assertEqual(result["per_plugin_evidence"]["LootTrackerPlugin"]["direct_indicators"], [])

    def test_text_block_and_character_literals_masked(self):
        text = 'class T { String s = """ } deleteStale(); """; char a = \'}\'; void f(){} }'
        masked = audit.mask_java(text)
        self.assertEqual(masked.count("{"), 2)
        self.assertEqual(masked.count("}"), 2)
        self.assertNotIn("deleteStale", masked)

    def test_nested_braces_constructor_parsed(self):
        body = "public Panel(){if(x){for(;;){new File(path).delete();}}}"
        masked = audit.mask_java(body)
        found = audit.method_bodies(masked, audit.constructor_pattern("Panel"))
        self.assertEqual(len(found), 1)
        self.assertEqual(audit.indicators(found[0]), ["cleanup"])

    def test_plugin_without_explicit_override_counted(self):
        self.files["source/rs/plugins/OtherPlugin.java"] = b"public class OtherPlugin extends Plugin {}"
        self.pack()
        result = self.scan()
        self.assertEqual(result["plugin_subclass_count"], 5)
        self.assertEqual(result["startup_override_count"], 4)
        self.assertEqual(result["without_explicit_startup_override"], ["OtherPlugin"])

    def test_annotation_type_reference_is_not_plugin_subclass(self):
        self.files["source/rs/plugins/PluginDependency.java"] = (
            b"public @interface PluginDependency { Class<? extends Plugin> value(); }")
        self.pack()
        result = self.scan()
        self.assertEqual(result["plugin_subclass_count"], 4)
        self.assertNotIn("PluginDependency", result["without_explicit_startup_override"])

    def test_duplicate_startup_override_refused(self):
        self.files["source/rs/plugins/loottracker/LootTrackerPlugin.java"] = (
            b"class LootTrackerPlugin extends Plugin { protected void startUp(){}"
            b" private void startUp(){} }")
        self.pack()
        with self.assertRaisesRegex(audit.Refused, "DUPLICATE_STARTUP_OVERRIDE"):
            self.scan()

    def test_unbalanced_method_refused(self):
        source = "public class X { protected void startUp(){ if(x){ action(); }"
        with self.assertRaisesRegex(audit.Refused, "UNBALANCED_METHOD_BRACES"):
            audit.method_bodies(audit.mask_java(source), audit.START)

    def test_missing_bootstrap_anchor_refused(self):
        del self.files["source/rs/pkg42/Class255.java"]
        self.pack()
        with self.assertRaisesRegex(audit.Refused, "STARTUP_ANCHORS_MISSING"):
            self.scan()

    def test_missing_swing_gate_refused(self):
        self.files["source/rs/plugins/PluginManager.java"] = b"class PluginManager{void startUp(){}}"
        self.pack()
        with self.assertRaisesRegex(audit.Refused, "STARTUP_EDT_SEQUENCE_NOT_VERIFIED"):
            self.scan()

    def test_no_plugin_classes_refused(self):
        for p in list(self.files):
            if p not in audit.REQUIRED and p.startswith("source/rs/plugins/"):
                self.files[p] = b"public class Example {}"
        self.pack()
        with self.assertRaisesRegex(audit.Refused, "PLUGIN_CLASSES_NOT_FOUND"):
            self.scan()

    def test_archive_sha_refused(self):
        with self.assertRaisesRegex(audit.Refused, "KIT_SHA256_DRIFT"):
            audit.pinned_archive(self.kit, "0"*64)

    def test_nonhex_sha_refused(self):
        with self.assertRaisesRegex(audit.Refused, "INVALID_SHA256_PIN"):
            audit.pinned_archive(self.kit, "wrong")

    def test_duplicate_archive_member_refused(self):
        items = list(self.files.items())
        self.pack(items + [items[0]])
        with self.assertRaisesRegex(audit.Refused, "DUPLICATE_ZIP_ENTRY"):
            audit.load_sources(self.kit, len(self.files))

    def test_parent_traversal_refused(self):
        self.pack(list(self.files.items()) + [("../private.txt", b"trap")])
        with self.assertRaisesRegex(audit.Refused, "UNSAFE_ZIP_ENTRY"):
            audit.load_sources(self.kit, len(self.files))

    def test_archive_symlink_refused(self):
        info = zipfile.ZipInfo("source/symlink.java")
        info.create_system = 3
        info.external_attr = ((stat.S_IFLNK | 0o777) << 16)
        self.assertFalse(audit.archive_safe(info))

    def test_directory_entry_allowed(self):
        self.assertTrue(audit.archive_safe(zipfile.ZipInfo("source/")))

    def test_source_size_refused(self):
        self.files["source/rs/pkg42/Class255.java"] = b"n"*(audit.MAX_SOURCE+1)
        self.pack()
        with self.assertRaisesRegex(audit.Refused, "SOURCE_SIZE_LIMIT"):
            audit.load_sources(self.kit, len(self.files))

    def test_invalid_zip_refused(self):
        self.kit.write_bytes(b"invalid ZIP")
        with self.assertRaisesRegex(audit.Refused, "KIT_READ_FAILED"):
            audit.load_sources(self.kit, len(self.files))

    def test_expected_source_count_refused(self):
        with self.assertRaisesRegex(audit.Refused, "SOURCE_COUNT_DRIFT"):
            audit.load_sources(self.kit, len(self.files)+1)

    def test_outfile_preexisting_refused(self):
        out = self.root / "report.json"
        out.write_text("KEEP", encoding="utf-8")
        args = ["--kit", str(self.kit), "--kit-sha256", self.digest(),
                "--expected-sources", str(len(self.files)), "--out", str(out)]
        self.assertEqual(audit.main(args), 2)
        self.assertEqual(out.read_text("utf-8"), "KEEP")

    def test_public_cli_writes_only_risk_flags(self):
        out = self.root / "new_report.json"
        args = ["--kit", str(self.kit), "--kit-sha256", self.digest(),
                "--expected-sources", str(len(self.files)), "--out", str(out)]
        self.assertEqual(audit.main(args), 0)
        report = json.loads(out.read_text("utf-8"))
        self.assertEqual(report["status"], "R393_STATIC_PLUGIN_STARTUP_RISK_INVENTORY")
        self.assertFalse(report["launch_authorized"])
        self.assertNotIn("source/rs/", out.read_text("utf-8"))

    def test_invalid_expected_source_count_refused(self):
        with self.assertRaisesRegex(audit.Refused, "INVALID_SOURCE_COUNT"):
            audit.load_sources(self.kit, 0)


if __name__ == "__main__":
    unittest.main()

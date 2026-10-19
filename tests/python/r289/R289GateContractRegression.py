#!/usr/bin/env python3
"""Independent public-source v309 R289 validation. No private game assets or GUI."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
R288 = ROOT / 'tools/windows/Invoke-R288-Owner-Acceptance.ps1'
R287 = ROOT / 'tools/windows/R287-Owner-Readiness.py'
R286 = ROOT / 'tools/windows/Invoke-R286-Guarded-Windows.ps1'
PINNED_R288 = '7f7be191dbc01cc3e2117d6ed005c34abc68811112cacb993843f87ef9a4ba32'
PINNED_R287 = '19bae667ea659924375c956acd1a9628c37784298434acfcfb76c5df743e1e5d'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class GateContract(unittest.TestCase):
    def test_original_r288_launcher_unchanged(self):
        self.assertEqual(digest(R288), PINNED_R288)

    def test_original_r287_probe_unchanged(self):
        self.assertEqual(digest(R287), PINNED_R287)

    def test_r286_launcher_available(self):
        self.assertTrue(R286.is_file())

    def test_gui_execution_requires_opt_in(self):
        s = R288.read_text()
        self.assertIn('[switch]$RunNativeGui', s)
        self.assertLess(s.index('if (-not $RunNativeGui)'), s.index('& powershell.exe -NoProfile'))

    def test_no_direct_game_launch_in_r288(self):
        s = R288.read_text()
        self.assertNotIn('rs.gui.Launcher', s)
        self.assertNotIn('taskkill /IM', s)
        self.assertIn('-File $R286Script', s)

    def test_sha_guards_before_source_extraction(self):
        s = R288.read_text()
        self.assertLess(s.index('$Actual -ne $PackageExpected'),s.index('ExtractToDirectory'))
        self.assertLess(s.index('$R286Hash -ne $R286ScriptExpected'),s.index('ExtractToDirectory'))

    def test_no_native_game_from_python(self):
        s = R287.read_text()
        self.assertNotIn('rs.gui.Launcher', s)
        self.assertIn('READ_ONLY_ADVISORY_NOT_GUI_ACCEPTANCE', s)

    def test_output_exists_rejected_before_extract(self):
        s = R288.read_text()
        self.assertLess(s.index('R288_REFUSE_EXISTING_OUTPUT'),s.index('ExtractToDirectory'))

    def test_native_only_gui(self):
        s = R288.read_text()
        self.assertIn('PlatformID]::Win32NT',s)
        self.assertIn('RunNativeGui',s)

    def test_r287_windows_native_api_fail_closed(self):
        s = R287.read_text()
        self.assertIn('SetProcessDpiAwarenessContext',s)
        self.assertIn("'valid': False",s)
        self.assertIn('127.0.0.1',s)

    def test_no_extracted_private_payloads(self):
        for name in ('*.jar','*.class','*.dat','*.idx','*.ttf','*.otf'):
            self.assertEqual(list(ROOT.glob('tools/windows/'+name)),[])

    def test_windows_negative_probes_reset_final_exit_status(self):
        ps = ROOT / 'tests/powershell/r289/Invoke-R289-SafeWindowsChecks.ps1'
        self.assertEqual(ps.read_text().strip().splitlines()[-1], 'exit 0')

    def test_wrong_public_inputs_refuse_without_new_output(self):
        with tempfile.TemporaryDirectory(prefix='r289-contract-') as t:
            input_dir = Path(t)/'inputs'
            input_dir.mkdir()
            output = Path(t)/'NEVER_CREATED'
            p = subprocess.run([sys.executable,str(R287),'--input-dir',str(input_dir),
                                '--output',str(output)],capture_output=True,text=True,timeout=15)
            self.assertEqual(p.returncode,2, p.stderr)
            report=json.loads(p.stdout)
            self.assertFalse(report['ready'])
            self.assertFalse(output.exists())
            self.assertEqual(report['type'],'READ_ONLY_ADVISORY_NOT_GUI_ACCEPTANCE')
            self.assertEqual(len(report['checks']),16)


if __name__=='__main__':
    unittest.main(verbosity=2)

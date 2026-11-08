"""Offline R354 mutation tests. No client or internet connection used."""
import copy
import json
import unittest
from pathlib import Path
from verify_r354 import decode, evaluate, HostInventoryRefused, FEATURES

HERE = Path(__file__).parent
BASE = json.loads((HERE / 'synthetic_host_disabled.json').read_text())

class HostPreflightTests(unittest.TestCase):
    def test_synthetic_disabled_host_is_consistent_but_not_admitted(self):
        result = evaluate(BASE)
        self.assertEqual(result['features']['Containers-DisposableClientVM'], 'disabled')
        self.assertTrue(result['hypervisor_present'])
        self.assertFalse(result['runtime_admitted'])
        self.assertFalse(result['os_egress_verified'])
        self.assertFalse(result['original_client_started'])

    def test_even_all_enabled_never_certifies_isolation(self):
        data = copy.deepcopy(BASE)
        data['features'] = {key: 1 for key in FEATURES}
        data['sandbox_executable_present'] = True
        result = evaluate(data)
        self.assertTrue(all(v == 'enabled' for v in result['features'].values()))
        self.assertFalse(result['runtime_admitted'])
        self.assertFalse(result['os_egress_verified'])

    def test_disabled_and_missing_not_conflated(self):
        for val, expected in [(1,'enabled'),(2,'disabled'),(3,'absent'),(4,'unknown'),(None,'not_observed')]:
            data = copy.deepcopy(BASE)
            data['features'][FEATURES[0]] = val
            self.assertEqual(evaluate(data)['features'][FEATURES[0]], expected)

    def test_reject_wrong_feature_type(self):
        for bad in [True, False, 0, -1, 5, '2', [], {}]:
            data = copy.deepcopy(BASE)
            data['features'][FEATURES[0]] = bad
            with self.subTest(bad=bad), self.assertRaises(HostInventoryRefused):
                evaluate(data)

    def test_forbid_auto_admission_and_fake_attestation(self):
        for name in ('runtime_admitted', 'os_egress_attested', 'original_client_started'):
            for bad in (True, 0, 1, 'false', None):
                data = copy.deepcopy(BASE)
                data[name] = bad
                with self.subTest(name=name,bad=bad), self.assertRaises(HostInventoryRefused):
                    evaluate(data)

    def test_reject_unexpected_and_missing_fields(self):
        for change in ('add', 'remove'):
            data = copy.deepcopy(BASE)
            if change == 'add': data['host_username'] = 'not_allowed'
            else: data.pop('features')
            with self.subTest(change=change), self.assertRaises(HostInventoryRefused):
                evaluate(data)

    def test_reject_bad_operating_system(self):
        for bad in [5, {}, [], 'Linux', '', 'N' * 161]:
            data = copy.deepcopy(BASE)
            data['operating_system'] = bad
            with self.subTest(bad=str(bad)[:20]), self.assertRaises(HostInventoryRefused):
                evaluate(data)

    def test_reject_bad_os_version(self):
        for bad in [None, True, '', '10', '10.0', '10.0.26300;evil', {}, []]:
            data = copy.deepcopy(BASE)
            data['os_version'] = bad
            with self.subTest(bad=str(bad)[:20]), self.assertRaises(HostInventoryRefused):
                evaluate(data)

    def test_reject_duplicate_json_keys(self):
        duplicate = json.dumps(BASE).replace('"runtime_admitted": false', '"runtime_admitted": false, "runtime_admitted": true')
        with self.assertRaises(HostInventoryRefused): decode(duplicate)

    def test_reject_oversize_json(self):
        with self.assertRaises(HostInventoryRefused): decode('x' * 16385)

    def test_reject_non_dictionary(self):
        for raw in ('[]', 'null', 'true', '5', '"string"'):
            with self.subTest(raw=raw), self.assertRaises(HostInventoryRefused): decode(raw)

    def test_readonly_powershell_contract_does_not_enable_features(self):
        script = (HERE/'r354_inventory.ps1').read_text(encoding='utf-8')
        required = ('Get-CimInstance', 'Win32_OptionalFeature', 'Win32_OperatingSystem',
                    'Win32_ComputerSystem', 'ConvertTo-Json')
        for marker in required: self.assertIn(marker, script)
        for forbidden in ('Enable-WindowsOptionalFeature', 'Disable-WindowsOptionalFeature',
                          'Set-NetFirewallRule', 'New-NetFirewallRule', 'Start-Process',
                          'Start-VM', 'wsl --install', 'java.exe', 'client.jar'):
            # ignore comment lines for source-only denylist assertion
            uncommented = '\n'.join(l for l in script.splitlines() if not l.lstrip().startswith('#'))
            self.assertNotIn(forbidden, uncommented)

if __name__ == '__main__': unittest.main(verbosity=2)

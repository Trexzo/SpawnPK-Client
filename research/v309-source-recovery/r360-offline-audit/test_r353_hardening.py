"""R353 synthetic fail-closed and malformed-input regressions. No original JAR launched."""
import copy
import unittest
from unittest.mock import patch
from test_r352 import SAMPLE
from run_r352 import execute, PreflightRefused
from verify_r352 import validate
from verify_receipt import ReceiptRefused

class R353HardeningTests(unittest.TestCase):
    def test_unhashable_phase_list_refused(self):
        x=copy.deepcopy(SAMPLE)
        x['phase']=['MAIN_RETURNED']
        with self.assertRaises(ReceiptRefused): validate(x)

    def test_unhashable_phase_mapping_refused(self):
        x=copy.deepcopy(SAMPLE)
        x['phase']={'danger': 'MAIN_RETURNED'}
        with self.assertRaises(ReceiptRefused): validate(x)

    def test_redacted_overflow_destination_accepted(self):
        x=copy.deepcopy(SAMPLE)
        x['endpoint_audit']['attempts'][0]['destination']='OTHER_OVERFLOW'
        self.assertEqual(validate(x)['dns_checks'],1)

    def test_alias_128_allowed(self):
        x=copy.deepcopy(SAMPLE)
        x['endpoint_audit']['attempts'][0]['destination']='OTHER_128'
        self.assertEqual(validate(x)['dns_checks'],1)

    def test_alias_129_refused(self):
        x=copy.deepcopy(SAMPLE)
        x['endpoint_audit']['attempts'][0]['destination']='OTHER_129'
        with self.assertRaises(ReceiptRefused): validate(x)

    def test_runtime_is_disabled_even_if_called_as_library(self):
        with patch('run_r352.subprocess.Popen') as popen:
            with self.assertRaisesRegex(PreflightRefused,'ORIGINAL_RUNTIME_DISABLED'):
                execute(jar='not-a-jar.jar',java='not-a-java.exe',classes='missing')
            popen.assert_not_called()

if __name__=='__main__': unittest.main(verbosity=2)

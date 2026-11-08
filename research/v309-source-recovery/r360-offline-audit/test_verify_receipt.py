"""Synthetic-only tests, no original client, no TCP/DNS."""
import copy
import unittest
from verify_receipt import evaluate, ReceiptRefused

GOOD = {
    "status":"R351_DENIED_ENDPOINT_DIAGNOSTIC_ONLY",
    "policy":"DENY_ALL_NETWORK",
    "dns_checks":1,"socket_checks":2,"overflow_checks":0,
    "attempts":[
        {"kind":"DNS_RESOLVE_CHECK", "destination":"KNOWN_GAME_HOST", "port":-1},
        {"kind":"SOCKET_CONNECT_CHECK", "destination":"KNOWN_GAME_HOST", "port":43594},
        {"kind":"SOCKET_CONNECT_CHECK", "destination":"OTHER_1", "port":443},
    ],
    "authenticated_login":"NOT_TESTED",
    "original_same_pid_reconnect":"NOT_TESTED",
    "original_inventory_recovery":"NOT_TESTED",
}
class TestReceipt(unittest.TestCase):
    def test_synthetic_valid(self):
        self.assertEqual(evaluate(GOOD)["status"], "R351_RECEIPT_CONSISTENT_ONLY")
    def test_reconnect_false_claim_rejected(self):
        x=copy.deepcopy(GOOD); x["original_same_pid_reconnect"]="PASS"
        with self.assertRaises(ReceiptRefused): evaluate(x)
    def test_unsanitized_host_rejected(self):
        x=copy.deepcopy(GOOD); x["attempts"][2]["destination"]="a.private.internal"
        with self.assertRaises(ReceiptRefused): evaluate(x)
    def test_dns_socket_confusion_rejected(self):
        x=copy.deepcopy(GOOD); x["attempts"][0]["kind"]="SOCKET_CONNECT_CHECK"
        with self.assertRaises(ReceiptRefused): evaluate(x)
    def test_total_wrong_rejected(self):
        x=copy.deepcopy(GOOD); x["socket_checks"]=3
        with self.assertRaises(ReceiptRefused): evaluate(x)
    def test_extra_claim_rejected(self):
        x=copy.deepcopy(GOOD); x["client_logged_in"]=True
        with self.assertRaises(ReceiptRefused): evaluate(x)
    def test_boolean_counter_rejected(self):
        x=copy.deepcopy(GOOD); x["dns_checks"]=True
        with self.assertRaises(ReceiptRefused): evaluate(x)
    def test_invalid_port_rejected(self):
        x=copy.deepcopy(GOOD); x["attempts"][1]["port"]=65536
        with self.assertRaises(ReceiptRefused): evaluate(x)

if __name__ == '__main__': unittest.main()

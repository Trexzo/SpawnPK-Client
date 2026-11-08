"""Only synthetic tests. No original v309 JAR, game server, cache, DNS or TCP."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from verify_r352 import validate, parse_console, PIN, PREFIX
from verify_receipt import ReceiptRefused
from run_r352 import admit_original, PreflightRefused, execute, sanitize_env

SAMPLE={
  "status":"R352_ORIGINAL_STARTUP_DENY_TRACE_ONLY",
  "original_jar_sha256":PIN,
  "launcher_class_verified":True,
  "original_main_invoked":True,
  "phase":"MAIN_RETURNED",
  "failure_type":"NONE",
  "windows_showing":1,
  "window_query_finished":True,
  "window_queries":2,
  "stdout_redirected":True,
  "endpoint_audit":{
      "status":"R351_DENIED_ENDPOINT_DIAGNOSTIC_ONLY","policy":"DENY_ALL_NETWORK",
      "dns_checks":1,"socket_checks":0,"overflow_checks":0,
      "attempts":[{"kind":"DNS_RESOLVE_CHECK","destination":"KNOWN_GAME_HOST","port":-1}],
      "authenticated_login":"NOT_TESTED","original_same_pid_reconnect":"NOT_TESTED",
      "original_inventory_recovery":"NOT_TESTED"},
  "login_verified":False,"same_pid_reconnect":"NOT_TESTED"
}

class TestR352(unittest.TestCase):
  def test_synthetic_receipt(self):
      parsed=parse_console("untrusted client log\n"+PREFIX+json.dumps(SAMPLE)+"\n")
      self.assertEqual(parsed["dns_checks"],1)
      self.assertEqual(parsed["socket_checks"],0)
      self.assertFalse(parsed["original_runtime_provenance_attested"])
  def test_multiple_receipts_denied(self):
      raw=PREFIX+json.dumps(SAMPLE)+"\n"
      with self.assertRaises(ReceiptRefused): parse_console(raw+raw)
  def test_missing_receipt_denied(self):
      with self.assertRaises(ReceiptRefused): parse_console("just original game log")
  def test_receipt_too_large_denied(self):
      with self.assertRaises(ReceiptRefused): parse_console("x"*65537)
  def test_duplicate_json_key_denied(self):
      raw=json.dumps(SAMPLE).replace('"phase":', '"phase":"MAIN_RETURNED","phase":',1)
      with self.assertRaises(ReceiptRefused): parse_console(PREFIX+raw)
  def test_false_login_denied(self):
      x=copy.deepcopy(SAMPLE);x["login_verified"]=True
      with self.assertRaises(ReceiptRefused):validate(x)
  def test_false_reconnect_denied(self):
      x=copy.deepcopy(SAMPLE);x["same_pid_reconnect"]="PASS"
      with self.assertRaises(ReceiptRefused):validate(x)
  def test_unknown_field_denied(self):
      x=copy.deepcopy(SAMPLE);x["password"]="oops"
      with self.assertRaises(ReceiptRefused):validate(x)
  def test_unredacted_host_denied(self):
      x=copy.deepcopy(SAMPLE);x["endpoint_audit"]["attempts"][0]["destination"]="private.example"
      with self.assertRaises(ReceiptRefused):validate(x)
  def test_bad_dns_port_denied(self):
      x=copy.deepcopy(SAMPLE);x["endpoint_audit"]["attempts"][0]["port"]=443
      with self.assertRaises(ReceiptRefused):validate(x)
  def test_main_requires_class_origin(self):
      x=copy.deepcopy(SAMPLE);x["launcher_class_verified"]=False
      with self.assertRaises(ReceiptRefused):validate(x)
  def test_unknown_original_jar_denied_before_process(self):
      with tempfile.TemporaryDirectory() as d:
          fake=Path(d)/"fake.jar";fake.write_bytes(b"not a jar")
          with patch("run_r352.subprocess.Popen") as popen:
              with self.assertRaises(PreflightRefused):
                  execute(jar=fake,java=fake,classes=d)
              popen.assert_not_called()
  def test_env_java_injection_removed(self):
      with patch.dict("run_r352.os.environ",{
          "JAVA_TOOL_OPTIONS":"-javaagent:evil.jar","JDK_JAVA_OPTIONS":"-XX:+Foo",
          "_JAVA_OPTIONS":"-Dsecret=1","CLASSPATH":"evil.jar"}):
          env=sanitize_env()
          for key in ("JAVA_TOOL_OPTIONS","JDK_JAVA_OPTIONS","_JAVA_OPTIONS","CLASSPATH"):
              self.assertNotIn(key,env)
  def test_full_child_output_not_reprinted(self):
      parsed=parse_console("password=never_publish\n"+PREFIX+json.dumps(SAMPLE)+"\n")
      self.assertNotIn("password",repr(parsed))

if __name__=="__main__":unittest.main(verbosity=2)

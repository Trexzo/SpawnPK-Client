"""R66 real Java9 original-vs-candidate CFG/exception parity tests."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from zipfile import ZipFile
from spk_recovery.bytecode_profile import profile_jar_class
from spk_recovery.large_method_cfg_parity import (
    LargeMethodParityError, compare_large_method_cfg,
    replay_private_large_method_cfg,
)

@unittest.skipUnless(shutil.which("javac"), "javac required")
class PrivateCfgParityTests(unittest.TestCase):
    def _jar(self, root, label, classname, names):
        src = root / label / "src" / "p" / (classname + ".java")
        out = root / label / "classes"
        src.parent.mkdir(parents=True)
        out.mkdir()
        a,b,c = names
        src.write_text(
            "package p; public final class " + classname
            + "{ public static int " + a + "," + b + "," + c + ";"
            + "public static void restore(boolean flag){"
            + "try {if(flag){" + a + "=11;}else{" + a + "=12;}"
            + b + "=" + a + "+3;}"
            + "catch(RuntimeException e){" + c + "=9;}"
            + "}}", encoding="utf-8")
        p = subprocess.run(["javac","--release","9","-g:none",
            "-proc:none","-d",str(out),str(src)],
            capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr+p.stdout)
        jar=root/(label+".jar")
        with ZipFile(jar,"w") as z:
            z.write(out/"p"/(classname+".class"),"p/"+classname+".class")
        return jar

    @staticmethod
    def _sha(jar):
        return hashlib.sha256(jar.read_bytes()).hexdigest()

    @staticmethod
    def _aliases():
        return [{"original":{"name":a,"descriptor":"I"},
                 "candidate":{"name":b,"descriptor":"I"}}
                for a,b in (("first","uno"),("second","dos"),("third","tres"))]

    def _pair(self,root):
        a=self._jar(root,"original","A",("first","second","third"))
        b=self._jar(root,"candidate","B",("uno","dos","tres"))
        return a,b,profile_jar_class(a,"p/A.class"),profile_jar_class(b,"p/B.class")

    def _check(self,source,candidate,aliases=None):
        return compare_large_method_cfg(
            source,"restore","(Z)V",candidate,"restore","(Z)V",
            self._aliases() if aliases is None else aliases)

    def test_original_and_candidate_jvm_structure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            a,b,source,candidate=self._pair(root)
            result=self._check(source,candidate)
            self.assertEqual(result["ordered_static_field_writes"],4)
            self.assertEqual(result["unique_mapped_original_owner_fields"],3)
            self.assertGreater(result["ordered_typed_exception_table_entries"],0)
            self.assertGreater(result["explicit_branch_edges"],0)
            self.assertTrue(result["exact_mapped_static_field_write_order"])
            self.assertFalse(result["runtime_equivalence_certified"])
            alias=root/"private-alias.json"
            alias.write_text(json.dumps({"schema_version":1,
                                          "aliases":self._aliases()}))
            report=replay_private_large_method_cfg(
                a,"p/A.class","restore","(Z)V",
                b,"p/B.class","restore","(Z)V",
                alias,root/"private",original_sha256=self._sha(a),
                candidate_sha256=self._sha(b))
            self.assertEqual(report["ordered_static_field_writes"],4)
            data=(root/"private"/"method-cfg-parity.aggregate.json").read_text()
            self.assertNotIn('"first"',data)
            self.assertNotIn('"uno"',data)

    def test_exception_table_and_branch_drift_veto(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            _,_,source,candidate=self._pair(root)
            method=next(m for m in candidate["methods"] if m["name"]=="restore")
            method["exception_handlers"][0]["catch_type"]="java/lang/Error"
            with self.assertRaisesRegex(
                LargeMethodParityError,"EXCEPTION_HANDLER_ORDER_OR_RANGE"):
                self._check(source,candidate)
            _,_,source,candidate=self._pair(Path(tmp)/"again")
            method=next(m for m in candidate["methods"] if m["name"]=="restore")
            jump=next(r for r in method["instructions"]
                      if "branch_target_offset" in r)
            jump["branch_target_offset"]=method["instructions"][0]["offset"]
            with self.assertRaisesRegex(
                LargeMethodParityError,"BRANCH_ORDINAL_TOPOLOGY"):
                self._check(source,candidate)

    def test_field_alias_and_whole_jar_pin_veto(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            a,b,source,candidate=self._pair(root)
            with self.assertRaisesRegex(
                LargeMethodParityError,"ALIASES_NOT_EXACTLY_COVERING_WRITES"):
                self._check(source,candidate,self._aliases()[:2])
            alias=root/"private-alias.json"
            alias.write_text(json.dumps({"schema_version":1,
                                          "aliases":self._aliases()}))
            with self.assertRaisesRegex(
                LargeMethodParityError,"PRIVATE_METHOD_CFG_PAIR_NOT_VERIFIABLE"):
                replay_private_large_method_cfg(
                    a,"p/A.class","restore","(Z)V",
                    b,"p/B.class","restore","(Z)V",
                    alias,root/"private",original_sha256="0"*64,
                    candidate_sha256=self._sha(b))
            self.assertFalse((root/"private").exists())

if __name__=="__main__":
    unittest.main()

"""R225 original callback source acceptance regression with unrelated JVM fixtures.

Hosted CI never receives or executes SpawnPK original client binaries or
actual Java. It tests exact 2/5-method decoded Code mappings, rejection of
changed predicates/owner aliases, SHA-pinned early return normalization,
and a Java9 compiler demonstration of the original callback guard shape.
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import unittest

from spk_recovery.private_v309_gambling_callback_original_code_r225 import (
    PACKET_METHODS,OVERLAY_METHODS,
    R225OriginalCallbacksError,
    EARLY_GUARD_BEFORE,EARLY_GUARD_AFTER,
    TRAILER_BEFORE,TRAILER_AFTER,
    normalize_original_readable_overlay_java,
    compare_callback_jvm_code,
    verify_private_original_gambling_callbacks,
)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def mapsha(value):
    return sha(json.dumps(value,sort_keys=True,separators=(",",":")).encode())


def synthesize_rows(real_specs,alias_at):
    # Borrow the non-proprietary public method signatures only, emitting
    # wholly invented instructions and synthetic owner identities.
    old=[];new=[];specs=[];symbols={}
    for i,(oh,rh,on,od,rn,rd,*_) in enumerate(real_specs):
        orig=[];translated=[]
        n=3 if i==alias_at else 2
        if i==alias_at:
            orig.append("       0: getstatic #2 // Field invented/Old.flag:Z")
            translated.append(
                "       0: getstatic #2 // Field invented/New.active:Z")
            orig.append("       3: iconst_1")
            translated.append("       3: iconst_1")
            ending=4
            ali={"Field invented/Old.flag:Z":
                 "Field invented/New.active:Z"}
            symbols.update(ali)
        else:
            orig.append("       0: iconst_1")
            translated.append("       0: iconst_1")
            ending=1;ali={}
        ret="ireturn" if "(Lrs/Client;)Z"==od else "return"
        orig.append(f"       {ending}: {ret}")
        translated.append(f"       {ending}: {ret}")
        old.extend((oh,"    Code:",*orig,""))
        new.extend((rh,"    Code:",*translated,""))
        specs.append((oh,rh,on,od,rn,rd,n,mapsha(ali)))
    return "\n".join(old),"\n".join(new),tuple(specs),symbols


class R225SyntheticOriginalCallbackCode(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (cls.packet_old,cls.packet_new,cls.packet_specs,
         cls.packet_symbols)=synthesize_rows(PACKET_METHODS,1)
        (cls.hud_old,cls.hud_new,cls.hud_specs,
         cls.hud_symbols)=synthesize_rows(OVERLAY_METHODS,3)

    def compare(self,which="packet",**kwargs):
        if which=="packet":
            old,new,rows,aliases=(self.packet_old,self.packet_new,
                                  self.packet_specs,self.packet_symbols)
        else:
            old,new,rows,aliases=(self.hud_old,self.hud_new,
                                  self.hud_specs,self.hud_symbols)
        params={
            "methods":rows,
            "original_total":sum(x[6] for x in rows),
            "alias_count":len(aliases),
            "alias_sha":mapsha(aliases),
        }
        params.update(kwargs)
        return compare_callback_jvm_code(old,new,**params)

    def test_packet_and_hud_complete_synthetic_code_pass(self):
        first=self.compare("packet")
        second=self.compare("hud")
        self.assertEqual(2,first["method_count"])
        self.assertEqual(5,second["method_count"])
        self.assertEqual(5,first["instruction_count"])
        self.assertEqual(11,second["instruction_count"])
        self.assertTrue(first["all_branch_offsets_and_constants_identical"])
        self.assertTrue(second["all_branch_offsets_and_constants_identical"])

    def test_changed_operand_and_wrong_symbol_mapping_rejected(self):
        bad=self.packet_new.replace(
            "Field invented/New.active:Z","Field invented/New.wrong:Z")
        with self.assertRaises(R225OriginalCallbacksError):
            compare_callback_jvm_code(
                self.packet_old,bad,methods=self.packet_specs,
                original_total=5,alias_count=1,
                alias_sha=mapsha(self.packet_symbols))
        with self.assertRaises(R225OriginalCallbacksError):
            self.compare("hud",alias_sha="0"*64)

    def test_changed_method_inventory_rejected(self):
        with self.assertRaises(R225OriginalCallbacksError):
            self.compare("packet",methods=self.packet_specs[:1])
        with self.assertRaises(R225OriginalCallbacksError):
            self.compare("hud",original_total=112)

    def test_exact_early_return_rewrite_and_sha_guard(self):
        raw=(
            "public class Invented {\n"
            " public void run(Object var2) {\n"
            "      if (var2 == Class69.field2525) {\n"
            "         int value = 5;\n"
            "      }\n"
            "   }\n\n"
            "   @Override\n"
            "   public void method904() {}\n"
            "}\n"
        )
        self.assertIn(EARLY_GUARD_BEFORE,raw)
        self.assertIn(TRAILER_BEFORE,raw)
        rewritten=(raw.replace(EARLY_GUARD_BEFORE,EARLY_GUARD_AFTER,1)
                     .replace(TRAILER_BEFORE,TRAILER_AFTER,1))
        self.assertEqual(
            rewritten,normalize_original_readable_overlay_java(
                raw,original_sha=sha(raw.encode()),
                normalized_sha=sha(rewritten.encode())))
        self.assertIn(EARLY_GUARD_AFTER,rewritten)
        self.assertNotIn(EARLY_GUARD_BEFORE,rewritten)
        for mutation in (
            raw.replace("var2 == Class69.field2525","var2 != Class69.field2525"),
            raw.replace("int value = 5;","int value = 6;"),
            raw+EARLY_GUARD_BEFORE,
        ):
            with self.subTest(last=mutation[-35:]):
                with self.assertRaises(R225OriginalCallbacksError):
                    normalize_original_readable_overlay_java(
                        mutation,
                        original_sha=sha(mutation.encode()),
                        normalized_sha=sha(rewritten.encode()))

    def test_original_java9_guard_compiler_branch_shape(self):
        if not shutil.which("javac") or not shutil.which("javap"):
            self.skipTest("Java compiler unavailable")
        cases={
            "Nested":"class Nested {static int a;"
                     "static void run(int x){if(x==2){a=5;}}}",
            "Early":"class Early {static int a;"
                    "static void run(int x){if(x!=2)return;a=5;}}",
        }
        with TemporaryDirectory(prefix="r225-invented-guard-") as td:
            root=Path(td);out=root/"classes";empty=root/"empty"
            out.mkdir();empty.mkdir()
            paths=[]
            for key,source in cases.items():
                path=root/(key+".java")
                path.write_text(source,encoding="utf-8")
                paths.append(str(path))
            build=subprocess.run([
                "javac","--release","9","-g:none","-proc:none",
                "-implicit:none","-classpath",str(empty),
                "-sourcepath",str(empty),"-d",str(out),*paths],
                capture_output=True,text=True,timeout=45,check=False)
            self.assertEqual(0,build.returncode,build.stderr)
            outputs={}
            for key in cases:
                outputs[key]=subprocess.run(
                    ["javap","-p","-c","-classpath",str(out),key],
                    capture_output=True,text=True,timeout=25,
                    check=True).stdout
        self.assertIn("if_icmp",outputs["Nested"])
        self.assertIn("if_icmp",outputs["Early"])
        self.assertNotEqual(outputs["Nested"],outputs["Early"])

    def test_private_original_inputs_fail_sha_check_before_compilation(self):
        with TemporaryDirectory(prefix="r225-forged-") as td:
            p=Path(td)/"not-client.jar"
            p.write_bytes(b"not an original client")
            with self.assertRaises(R225OriginalCallbacksError):
                verify_private_original_gambling_callbacks(p,p,p)


if __name__=="__main__":
    unittest.main()

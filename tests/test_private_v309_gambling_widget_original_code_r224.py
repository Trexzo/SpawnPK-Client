"""R224 synthetic (non-SpawnPK) six-method JVM Code comparator regression.

Original source, proprietary v309 JAR and compiled game classes are never
included in hosted CI. A separate small Java9 fixture checks why += / -=
rather than a manually expanded assignment is necessary for dup2 parity.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
from hashlib import sha256
import json
import re
import shutil
import subprocess
import unittest

from spk_recovery.private_v309_gambling_widget_original_code_r224 import (
    METHODS, BEFORE_AFTER,
    R224GamblingWidgetParityError,
    normalize_exact_gambling_source,
    verify_original_class170_code,
    verify_private_original_gambling_widget,
)


def hashed(mapping):
    return sha256(json.dumps(mapping,sort_keys=True,
        separators=(",",":")).encode()).hexdigest()


class R224SyntheticJVMCodeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.methods=[]
        left=[]
        right=[]
        cls.symbol_mapping={
            "Field toy/Legacy.flag:Z":"Field toy/Readable.enabled:Z",
        }
        for i,(before,after,_,_,_,_,_,_) in enumerate(METHODS):
            # Small purpose-built methods with correct method-specific
            # uniqueness, without embedding or deriving any game code.
            first=i==2
            nops=3 if first else 2
            left.extend((before,"    Code:"))
            right.extend((after,"    Code:"))
            if first:
                left.append("       0: getstatic #1 // Field toy/Legacy.flag:Z")
                right.append("       0: getstatic #1 // Field toy/Readable.enabled:Z")
                left.append("       3: iconst_1")
                right.append("       3: iconst_1")
                end=4
                aliases=cls.symbol_mapping
            else:
                left.append("       0: iconst_1")
                right.append("       0: iconst_1")
                end=1
                aliases={}
            final="areturn" if i==4 else "return"
            left.append(f"       {end}: {final}")
            right.append(f"       {end}: {final}")
            left.append("");right.append("")
            cls.methods.append(
                (before,after,*METHODS[i][2:6],nops,hashed(aliases)))
        cls.old="\n".join(left)
        cls.new="\n".join(right)
        cls.expected=tuple(cls.methods)

    def proof(self, new=None, **changes):
        settings=dict(methods=self.expected,
                      original_total=13,
                      global_alias_sha=hashed(self.symbol_mapping),
                      expected_alias_count=1)
        settings.update(changes)
        return verify_original_class170_code(self.old,new or self.new,
                                              **settings)

    def test_six_synthetic_methods_and_one_consistent_symbol_map(self):
        x=self.proof()
        self.assertEqual(6,x["original_JVM_methods_verified"])
        self.assertEqual(13,x["original_JVM_instructions_verified"])
        self.assertEqual(1,x["distinct_symbol_aliases_verified"])
        self.assertFalse(x["complete_client_source_compiled"])

    def test_changed_operand_and_opcode_and_offset_rejected(self):
        for changed in (
            self.new.replace("Field toy/Readable.enabled:Z",
                             "Field toy/Readable.other:Z"),
            self.new.replace("iconst_1","iconst_0",1),
            self.new.replace("       3: iconst_1","       4: iconst_1"),
            self.new.replace("       0: iconst_1","       0: nop",1),
        ):
            with self.subTest(mutant=changed[:50]):
                with self.assertRaises(R224GamblingWidgetParityError):
                    self.proof(new=changed)

    def test_wrong_method_count_and_alias_pins_rejected(self):
        with self.assertRaises(R224GamblingWidgetParityError):
            self.proof(original_total=954)
        with self.assertRaises(R224GamblingWidgetParityError):
            self.proof(global_alias_sha="0"*64)
        changed=list(self.expected)
        a=list(changed[2]);a[-1]="0"*64;changed[2]=tuple(a)
        with self.assertRaises(R224GamblingWidgetParityError):
            self.proof(methods=tuple(changed))

    def test_normalization_requires_exact_two_edits(self):
        data="\n".join(("class Invented {",
            BEFORE_AFTER[0][0],BEFORE_AFTER[1][0],"}"))+"\n"
        orig=sha256(data.encode()).hexdigest()
        normalized=data
        for before,after in BEFORE_AFTER:
            normalized=normalized.replace(before,after,1)
        pin=sha256(normalized.encode()).hexdigest()
        self.assertEqual(
            normalized,normalize_exact_gambling_source(
                data,source_sha=orig,normalized_sha=pin))
        for mutant in (
            data.replace("- 9","- 10"),
            data+BEFORE_AFTER[0][0],
            data.replace(BEFORE_AFTER[1][0],"var1.childY[var6] = 1;"),
        ):
            with self.assertRaises(R224GamblingWidgetParityError):
                normalize_exact_gambling_source(
                    mutant,source_sha=sha256(mutant.encode()).hexdigest(),
                    normalized_sha=pin)

    def test_java9_compiler_replaces_two_array_reloads_with_dup2(self):
        if not shutil.which("javac") or not shutil.which("javap"):
            self.skipTest("Java compiler tools missing")
        srcs={
            "Expanded":(
                "class Expanded {int[] values;"
                "void change(int i){values[i]=values[i]-9;"
                "values[i]=values[i]+13;}}"
            ),
            "Compound":(
                "class Compound {int[] values;"
                "void change(int i){values[i]-=9;values[i]+=13;}}"
            ),
        }
        with TemporaryDirectory(prefix="r224-unrelated-java9-") as td:
            root=Path(td);out=root/"classes";empty=root/"empty"
            out.mkdir();empty.mkdir()
            for name,source in srcs.items():
                (root/(name+".java")).write_text(source)
            result=subprocess.run(
                ["javac","--release","9","-g:none","-proc:none",
                 "-implicit:none","-classpath",str(empty),
                 "-sourcepath",str(empty),"-d",str(out),
                 str(root/"Expanded.java"),str(root/"Compound.java")],
                capture_output=True,text=True,timeout=45,check=False)
            self.assertEqual(result.returncode,0,result.stderr)
            compiled={}
            for name in srcs:
                compiled[name]=subprocess.run(
                    ["javap","-p","-c","-classpath",str(out),name],
                    capture_output=True,text=True,check=True,timeout=25).stdout
        expanded=compiled["Expanded"]
        compound=compiled["Compound"]
        self.assertEqual(2,compound.count("dup2"))
        self.assertEqual(0,expanded.count("dup2"))
        self.assertGreater(expanded.count("getfield"),
                           compound.count("getfield"))

    def test_real_binary_inputs_must_be_pinned(self):
        with TemporaryDirectory() as td:
            fake=Path(td)/"wrong.jar"
            fake.write_bytes(b"not an original client")
            with self.assertRaises(R224GamblingWidgetParityError):
                verify_private_original_gambling_widget(fake,fake,fake)


if __name__=="__main__":
    unittest.main()

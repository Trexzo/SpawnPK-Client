"""R181 uses synthetic Java9 classfiles only; no original client inputs."""
import hashlib
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile, ZIP_DEFLATED

from spk_recovery.private_v309_packet_helper_frontier_r181 import (
    audit_packet_helper_frontier, R181HelperFrontierError,
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class R181SyntheticHelperFrontierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("javac"):
            raise unittest.SkipTest("Java JDK required")
        cls.temp=TemporaryDirectory(prefix="r181-synthetic-")
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root=Path(cls.temp.name)
        cls.sources={
            "rs/x/e.java":(
                "package rs.x; public class e {"
                " private rs.q.a q = new rs.q.a();"
                " public int use(rs.v.a v) {"
                " return q.read() + v.read() + rs.h.value"
                " + new rs.f.a().read();"
                " }"
                "}"),
            "rs/q/a.java":(
                "package rs.q; public class a {"
                " public int read(){return 1;}"
                "}"),
            "rs/v/a.java":(
                "package rs.v; public class a {"
                " public int read(){return 2;}"
                "}"),
            "rs/h.java":(
                "package rs; public class h {"
                " public static int value=3;"
                "}"),
            "rs/f/a.java":(
                "package rs.f; public class a {"
                " public int read(){return 4;}"
                "}"),
        }
        src=cls.root/"src"
        dest=cls.root/"classes"
        empty=cls.root/"empty"
        dest.mkdir(); empty.mkdir()
        javafiles=[]
        for name,body in cls.sources.items():
            path=src/name
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(body,encoding="utf-8")
            javafiles.append(str(path))
        proc=subprocess.run(
            ["javac","--release","9","-g:none","-proc:none",
             "-implicit:none","-classpath",str(empty),
             "-sourcepath",str(empty),"-d",str(dest),*javafiles],
            capture_output=True,text=True,check=False,timeout=90)
        if proc.returncode:
            raise AssertionError("Synthetic JDK build failed: "+proc.stderr)
        cls.owners=("rs/q/a","rs/v/a","rs/h","rs/f/a")
        cls.jar=cls.root/"original-synthetic.jar"
        with ZipFile(cls.jar,"w",ZIP_DEFLATED) as output:
            for f in sorted(dest.rglob("*.class")):
                output.write(f,f.relative_to(dest).as_posix())
        cls.jar_sha=sha(cls.jar)
        with ZipFile(cls.jar) as original:
            cls.packet_sha=hashlib.sha256(
                original.read("rs/x/e.class")).hexdigest()
            cls.helper_shas={x:hashlib.sha256(
                original.read(x+".class")).hexdigest()
                for x in cls.owners}

    def inspect(self,**kwargs):
        params={
            "original_sha256":self.jar_sha,
            "packet_class_sha256":self.packet_sha,
            "expected_helper_class_sha256":self.helper_shas,
        }
        params.update(kwargs)
        return audit_packet_helper_frontier(self.jar,**params)

    def test_exact_abi_and_direct_reference_counts(self):
        r=self.inspect()
        self.assertTrue(r["four_original_helper_classes_present"])
        self.assertTrue(r["helper_class_sha256_separately_pinned"])
        self.assertEqual(4,len(r["helpers"]))
        self.assertEqual(set(self.owners),{x["owner"] for x in r["helpers"]})
        self.assertEqual(4,len(set(x["original_class_sha256"]
                                   for x in r["helpers"])))
        self.assertGreaterEqual(
            sum(x["distinct_packet_method_calls"] for x in r["helpers"]),3)
        self.assertGreaterEqual(
            sum(x["distinct_packet_field_accesses"] for x in r["helpers"]),1)
        self.assertGreaterEqual(
            sum(x["packet_signature_type_references"] for x in r["helpers"]),1)
        self.assertTrue(all(x["original_jvm_instructions"]>0
                            for x in r["helpers"]))
        self.assertFalse(r["helper_java_source_equivalence_verified"])
        self.assertFalse(r["complete_runtime_or_reflection_dependency_closure"])
        self.assertFalse(r["full_v309_client_compilation_proven"])
        self.assertFalse(r["original_game_code_executed"])

    def test_stable_private_manifest_and_private_disclosure_opt_in(self):
        a=self.inspect()
        b=self.inspect()
        self.assertEqual(a,b)
        self.assertNotIn("private_original_helper_member_worklist",a)
        details=self.inspect(include_private_names=True)
        self.assertEqual(a["private_member_worklist_sha256"],
                         details["private_member_worklist_sha256"])
        self.assertEqual(4,len(details[
            "private_original_helper_member_worklist"]))
        self.assertTrue(any(
            member[3]=="read"
            for row in details["private_original_helper_member_worklist"]
            for member in row["packet_invocations"]))

    def test_optional_source_is_only_presence_not_acceptance(self):
        candidate=self.root/"source-candidate.zip"
        with ZipFile(candidate,"w",ZIP_DEFLATED) as output:
            output.writestr("recovered-source/v309/src/rs/h.java",
                            self.sources["rs/h.java"])
        result=self.inspect(private_source_candidate_zip=candidate,
                            candidate_source_sha256=sha(candidate))
        found={x["owner"]:x["candidate_source_path_present_unverified"]
               for x in result["helpers"]}
        self.assertEqual(True,found["rs/h"])
        self.assertEqual(False,found["rs/q/a"])
        self.assertFalse(result["helper_java_source_equivalence_verified"])

    def test_wrong_jar_packet_or_helper_digest_fails_closed(self):
        for override in (
            {"original_sha256":"0"*64},
            {"packet_class_sha256":"0"*64},
            {"expected_helper_class_sha256":{
                **self.helper_shas,"rs/h":"0"*64}},
        ):
            with self.subTest(override=list(override)):
                with self.assertRaises(R181HelperFrontierError):
                    self.inspect(**override)

    def test_missing_helper_and_wrong_owner_inventory_rejected(self):
        truncated=self.root/"truncated.jar"
        with ZipFile(self.jar) as original, ZipFile(truncated,"w") as dest:
            for f in original.namelist():
                if f!="rs/h.class":
                    dest.writestr(f,original.read(f))
        with self.assertRaises(R181HelperFrontierError):
            audit_packet_helper_frontier(
                truncated,original_sha256=sha(truncated),
                packet_class_sha256=self.packet_sha,
                helper_owners=self.owners)
        with self.assertRaises(R181HelperFrontierError):
            self.inspect(helper_owners=("rs/q/a","rs/q/a","rs/h","rs/f/a"))

    def test_private_source_sha_pair_required(self):
        with self.assertRaises(R181HelperFrontierError):
            self.inspect(candidate_source_sha256="0"*64)
        with self.assertRaises(R181HelperFrontierError):
            self.inspect(private_source_candidate_zip=self.jar)


if __name__=="__main__":
    unittest.main()

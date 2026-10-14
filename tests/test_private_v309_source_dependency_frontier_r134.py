"""R134: synthetic original-vs-decompiler dependency boundary tests."""
import unittest

from spk_recovery.private_v309_source_dependency_frontier_r134 import (
    source_dependency_provenance,
)


class PrivateSourceDependencyR134Tests(unittest.TestCase):
    def setUp(self):
        self.entries = [
            ("rs/Recovered.java", b"""
package rs;
import java.util.List;
import com.google.gson.Gson;
import com.google.gson.annotations.SerializedName;
import org.apache.commons.a.F;
import org.apache.commons.a.d_;
import rs.Client;
import rs.SomeRecovered;
import rs.Container.Inner;
import static org.apache.commons.a.F.test;
import rs.unknown.*;
public class Recovered { }
"""),
            ("rs/SomeRecovered.java", b"package rs; public class SomeRecovered {}"),
        ]
        self.original = {
            "rs/Client", "org/apache/commons/a/F", "rs/Container",
        }

    def test_absent_gson_is_not_mislabeled_original_requirement(self):
        report = source_dependency_provenance(
            self.entries, self.original, include_private_names=True)
        rows = {e["java_import"]: e
                for e in report["private_import_evidence"]}
        self.assertEqual(
            rows["com.google.gson.Gson"]["source_import_evidence"],
            "not_found_by_exact_original_or_source_path")
        self.assertEqual(
            rows["org.apache.commons.a.d_"]["source_import_evidence"],
            "not_found_by_exact_original_or_source_path")
        self.assertFalse(
            rows["com.google.gson.Gson"]["is_original_dependency_certified"])
        self.assertFalse(
            rows["com.google.gson.Gson"]["is_user_added_code_certified"])

    def test_original_external_class_and_source_path_separately_reported(self):
        report = source_dependency_provenance(
            self.entries, self.original, include_private_names=True)
        rows = {e["java_import"]: e
                for e in report["private_import_evidence"]}
        self.assertEqual(rows["org.apache.commons.a.F"][
            "source_import_evidence"], "exact_original_class_path_present")
        self.assertEqual(rows["rs.SomeRecovered"][
            "source_import_evidence"],
            "source_file_path_present_original_unverified")
        self.assertEqual(rows["rs.Container.Inner"][
            "source_import_evidence"],
            "possible_original_nested_class_unverified")

    def test_underscore_alias_correlates_with_actual_jvm_shadow_only(self):
        original = self.original | {
            "org/apache/commons/a/d",
            "org/apache/commons/a/d/Inner"
        }
        report = source_dependency_provenance(
            self.entries, original, include_private_names=True)
        rows = {row["java_import"]: row
                for row in report["private_import_evidence"]}
        self.assertEqual(
            rows["org.apache.commons.a.d_"]["source_import_evidence"],
            "possible_original_shadow_alias_unverified")
        self.assertFalse(
            rows["org.apache.commons.a.d_"][
                "is_original_dependency_certified"])
        self.assertFalse(
            rows["org.apache.commons.a.d_"][
                "is_user_added_code_certified"])

    def test_underscore_without_shadow_not_accepted_as_alias(self):
        report = source_dependency_provenance(
            self.entries, self.original, include_private_names=True)
        rows = {row["java_import"]: row
                for row in report["private_import_evidence"]}
        self.assertEqual(rows["org.apache.commons.a.d_"][
            "source_import_evidence"],
            "not_found_by_exact_original_or_source_path")

    def test_static_wildcard_and_jdk_imports_not_false_exact(self):
        report = source_dependency_provenance(
            self.entries, self.original, include_private_names=True)
        rows = {e["java_import"]: e
                for e in report["private_import_evidence"]}
        self.assertEqual(rows["java.util.List"]["source_import_evidence"],
                         "jdk_namespace_or_external_api_unverified")
        self.assertEqual(rows["rs.unknown.*"]["source_import_evidence"],
                         "wildcard_or_static_not_resolved")
        self.assertEqual(rows["org.apache.commons.a.F.test"][
            "source_import_evidence"], "wildcard_or_static_not_resolved")

    def test_public_default_has_no_file_paths_or_import_names(self):
        report = source_dependency_provenance(
            self.entries, self.original)
        self.assertNotIn("private_import_evidence", report)
        self.assertFalse(
            report["original_dependency_ownership_certified"])
        self.assertFalse(
            report["missing_import_proves_nonoriginal_source"])
        self.assertFalse(
            report["decompiled_candidate_is_equivalent_to_original"])

    def test_input_order_cannot_change_manifest(self):
        one = source_dependency_provenance(
            self.entries, self.original)
        two = source_dependency_provenance(
            list(reversed(self.entries)), self.original)
        self.assertEqual(one["private_row_manifest_sha256"],
                         two["private_row_manifest_sha256"])
        self.assertEqual(one["classifications"], two["classifications"])

    def test_original_empty_set_is_not_proof_of_missing_classes(self):
        report = source_dependency_provenance(
            self.entries, set())
        self.assertFalse(report["missing_import_proves_nonoriginal_source"])
        self.assertFalse(report["original_dependency_ownership_certified"])

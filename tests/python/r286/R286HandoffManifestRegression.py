#!/usr/bin/env python3
"""Source-free R286 release archive gate. No private game binaries or Windows claims."""
import hashlib
import json
import sys
import zipfile


def verify(path):
    checks = 0

    def ck(condition, label):
        nonlocal checks
        if not condition:
            raise AssertionError("R286_RELEASE_FAIL " + label)
        checks += 1

    with zipfile.ZipFile(path) as archive:
        ck(archive.testzip() is None, "ZIP CRC")
        manifest = json.loads(archive.read("MANIFEST.json"))
        ck(manifest["milestone"] == "R286", "milestone")
        ck(manifest["production_changes"] == 0, "production source changed")
        ck(manifest["native_windows_gui"] == "NOT_TESTED", "false Windows acceptance")
        ck(set(archive.namelist()) == set(manifest["files"]) | {"MANIFEST.json"}, "file set")
        for name, info in manifest["files"].items():
            data = archive.read(name)
            ck(len(data) == info["bytes"], "size " + name)
            ck(hashlib.sha256(data).hexdigest() == info["sha256"], "hash " + name)
            ck(not name.lower().endswith((".jar", ".class", ".dat", ".idx", ".ttf", ".otf")), "private binary " + name)
        tests = archive.read("evidence/R286_UNIT_TESTS.log").decode()
        ck("Ran 19 tests" in tests and "\nOK\n" in tests, "safety regression")
        extracted = archive.read("evidence/R286_PACKAGE_EXTRACTED_REGRESSION.log").decode()
        ck("Ran 19 tests" in extracted and "\nOK\n" in extracted, "extracted source regression")
        stage = archive.read("evidence/R286_REAL_STAGE_COMPILE.log").decode()
        ck('"staged_assets": 10772' in stage, "authentic cache staging")
        ck("R286_AWT_JAVA11_COMPILATION_PASS classes=2" in stage, "JDK11 helper compilation")
        ck("R286_STAGED_PRIVATE_JAR_VERIFIED dbaeaef9b375c8a99a6138075bed4ba71ef71ad2d82e8417ae36b400bd4828bd" in stage, "R278 pin")
        prior = archive.read("evidence/R285_PRIOR_EVIDENCE_RECHECK.log").decode()
        ck("checks=228" in prior, "prior GUI evidence")
        ck("R286_REFUSE_NOT_NATIVE_WINDOWS" in archive.read("evidence/R286_NATIVE_OS_REFUSAL.log").decode(), "OS fail-closed")
        ck("R286_READ_ONLY_PINNED_INPUT_PREFLIGHT_PASS" in archive.read("evidence/R286_REAL_INPUT_PREFLIGHT.log").decode(), "actual archive preflight")
        launcher = archive.read("scripts/R286-Windows-Acceptance.py").decode()
        for guard in ("reject_output(out)", "verify_inputs(inputs)", "check_desktop()", "ensure_local_port_free()", "stage_private_home(out, inputs)"):
            ck(guard in launcher, guard)
        supervisor = archive.read("scripts/probe/run_r286_windows_gui.py").decode()
        for guard in ("validate_client_window(client.pid)", "R286_REFUSE_NOT_NATIVE_WINDOWS", "actual_cook_packet_received", "taskkill"):
            ck(guard in supervisor, guard)

    print("R286_GITHUB_RELEASE_GATE_PASS checks=" + str(checks) + " native_windows=NOT_TESTED")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python R286HandoffManifestRegression.py <R286_source_only.zip>")
    verify(sys.argv[1])

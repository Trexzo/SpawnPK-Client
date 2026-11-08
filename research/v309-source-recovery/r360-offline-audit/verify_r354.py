"""R354: strict classification of read-only host inventory, never OS attestation.

No network, client launch, system configuration, or runtime enablement.
Receipt JSON is untrusted: a syntactically valid report never proves OS egress.
"""
from __future__ import annotations
import json
import re
import sys
from pathlib import Path

class HostInventoryRefused(ValueError):
    pass

FEATURES = (
    "Containers-DisposableClientVM",
    "Microsoft-Hyper-V-All",
    "VirtualMachinePlatform",
    "HypervisorPlatform",
    "Microsoft-Windows-Subsystem-Linux",
)
TOP_FIELDS = {
    "schema", "source", "operating_system", "os_version", "hypervisor_present",
    "sandbox_executable_present", "features", "runtime_admitted",
    "os_egress_attested", "original_client_started",
}


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise HostInventoryRefused("R354_DUPLICATE_FIELD")
        result[key] = value
    return result


def decode(raw: str):
    if not isinstance(raw, str) or len(raw) > 16384:
        raise HostInventoryRefused("R354_INVALID_INPUT_LENGTH")
    try:
        record = json.loads(raw, object_pairs_hook=unique_pairs)
    except ValueError as e:
        raise HostInventoryRefused("R354_INVALID_JSON") from e
    return evaluate(record)


def evaluate(data):
    if type(data) is not dict or set(data) != TOP_FIELDS:
        raise HostInventoryRefused("R354_UNEXPECTED_FIELDS")
    if data["schema"] != "R354_READ_ONLY_WINDOWS_FEATURE_INVENTORY_V1":
        raise HostInventoryRefused("R354_INVALID_SCHEMA")
    if data["source"] != "Win32_OptionalFeature+Win32_OperatingSystem+Win32_ComputerSystem":
        raise HostInventoryRefused("R354_INVALID_SOURCE")
    if type(data["operating_system"]) is not str or not 1 <= len(data["operating_system"]) <= 160:
        raise HostInventoryRefused("R354_INVALID_OS_NAME")
    if not data["operating_system"].casefold().startswith("microsoft windows"):
        raise HostInventoryRefused("R354_WRONG_OPERATING_SYSTEM")
    if type(data["os_version"]) is not str or not re.fullmatch(r"\d{1,5}\.\d{1,5}\.\d{1,6}(?:\.\d{1,6})?", data["os_version"]):
        raise HostInventoryRefused("R354_INVALID_OS_VERSION")
    for field in ("hypervisor_present", "sandbox_executable_present"):
        if type(data[field]) is not bool:
            raise HostInventoryRefused("R354_BAD_BOOLEAN_" + field)
    for field in ("runtime_admitted", "os_egress_attested", "original_client_started"):
        if data[field] is not False:
            raise HostInventoryRefused("R354_UNPROVEN_TRUE_CLAIM_" + field)
    features = data["features"]
    if type(features) is not dict or set(features) != set(FEATURES):
        raise HostInventoryRefused("R354_BAD_FEATURE_SET")
    for name, state in features.items():
        if state is not None and (type(state) is not int or state not in (1, 2, 3, 4)):
            raise HostInventoryRefused("R354_BAD_FEATURE_STATE_" + name)
    return {
        "status": "R354_HOST_INVENTORY_CONSISTENT_NOT_ATTESTED",
        "os": data["operating_system"],
        "os_version": data["os_version"],
        "features": {name: {1: "enabled", 2: "disabled", 3: "absent", 4: "unknown", None: "not_observed"}[features[name]] for name in FEATURES},
        "hypervisor_present": data["hypervisor_present"],
        "sandbox_executable_present": data["sandbox_executable_present"],
        "os_egress_verified": False,
        "runtime_admitted": False,
        "original_client_started": False,
        "next_requirement": "INDEPENDENTLY_VERIFIED_OS_EGRESS_ISOLATION_AND_SCRATCH_ENVIRONMENT",
    }


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("usage: python verify_r354.py <read-only-inventory.json>", file=sys.stderr)
        return 2
    try:
        result = decode(Path(argv[0]).read_text(encoding="utf-8-sig"))
    except (OSError, HostInventoryRefused) as e:
        print(json.dumps({"status": "R354_INVENTORY_REFUSED", "reason": str(e)}))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

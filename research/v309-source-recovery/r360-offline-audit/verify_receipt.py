"""Fail-closed, source-only admission for R351 diagnostic receipts.

No live game is ever invoked. Do not interpret a receipt as OS-origin attestation.
"""
import json
import re
import sys
from pathlib import Path

class ReceiptRefused(ValueError):
    pass


def strict_json(path):
    def unique(pairs):
        out = {}
        for key, value in pairs:
            if key in out:
                raise ReceiptRefused("DUPLICATE_KEY")
            out[key] = value
        return out
    return json.loads(Path(path).read_text(encoding="utf-8-sig"), object_pairs_hook=unique)


def evaluate(x):
    if not isinstance(x, dict) or set(x) != {
        "status", "policy", "dns_checks", "socket_checks", "overflow_checks",
        "attempts", "authenticated_login", "original_same_pid_reconnect",
        "original_inventory_recovery"
    }:
        raise ReceiptRefused("UNKNOWN_OR_MISSING_FIELDS")
    if x["status"] != "R351_DENIED_ENDPOINT_DIAGNOSTIC_ONLY" or x["policy"] != "DENY_ALL_NETWORK":
        raise ReceiptRefused("INVALID_POLICY_OR_STATUS")
    if any(x[k] != "NOT_TESTED" for k in (
        "authenticated_login", "original_same_pid_reconnect", "original_inventory_recovery")):
        raise ReceiptRefused("FALSE_RUNTIME_ACCEPTANCE")
    for key in ("dns_checks", "socket_checks", "overflow_checks"):
        if type(x[key]) is not int or not 0 <= x[key] <= 1000000:
            raise ReceiptRefused("INVALID_COUNT_" + key)
    items = x["attempts"]
    if not isinstance(items, list) or len(items) > 128:
        raise ReceiptRefused("INVALID_ATTEMPT_LIST")
    for attempt in items:
        if not isinstance(attempt, dict) or set(attempt) != {"kind", "destination", "port"}:
            raise ReceiptRefused("INVALID_ATTEMPT_FIELDS")
        kind, dest, port = (attempt[k] for k in ("kind", "destination", "port"))
        if kind not in ("DNS_RESOLVE_CHECK", "SOCKET_CONNECT_CHECK"):
            raise ReceiptRefused("INVALID_EVENT_TYPE")
        if type(port) is not int or not -1 <= port <= 65535:
            raise ReceiptRefused("INVALID_PORT")
        if (kind == "DNS_RESOLVE_CHECK") != (port == -1):
            raise ReceiptRefused("INCONSISTENT_RESOLVE_PORT")
        if not isinstance(dest, str) or not re.fullmatch(r"KNOWN_GAME_HOST|LOOPBACK|UNKNOWN_EMPTY|OTHER_OVERFLOW|OTHER_(?:[1-9]|[1-9][0-9]|1[01][0-9]|12[0-8])", dest):
            raise ReceiptRefused("UNSANITIZED_DESTINATION")
    total = x["dns_checks"] + x["socket_checks"]
    if total != len(items) + x["overflow_checks"]:
        raise ReceiptRefused("INCONSISTENT_TOTAL")
    if x["overflow_checks"] and len(items) != 128:
        # Smaller local caps are supported by Java contract tests; the
        # production diagnostic's cap is explicitly fixed at 128.
        raise ReceiptRefused("NONSTANDARD_CAP_OR_OVERFLOW")
    return {
        "status": "R351_RECEIPT_CONSISTENT_ONLY",
        "dns_checks": x["dns_checks"],
        "socket_checks": x["socket_checks"],
        "unknown_host_groups": len(set(a["destination"] for a in items if a["destination"].startswith("OTHER_"))),
        "original_v309_runtime_provenance_attested": False,
        "same_pid_reconnect": "NOT_TESTED",
    }


def main(argv):
    if len(argv) != 2:
        print("usage: python verify_receipt.py receipt.json", file=sys.stderr)
        return 2
    try:
        result = evaluate(strict_json(argv[1]))
    except (ReceiptRefused, OSError, ValueError) as exc:
        print(json.dumps({"status":"R351_RECEIPT_REFUSED","reason":str(exc)}))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

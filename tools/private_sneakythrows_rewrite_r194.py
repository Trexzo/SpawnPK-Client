"""Private, opt-in source repair for Lombok @SneakyThrows decompilation candidates.

Never uploads recovered Java. Fail-closed input ZIP/member hashes must be
supplied by a reviewed manifest. Always produces a NEW private output ZIP.
An annotation removal wraps each method body in a catch-and-rethrow preserving
the actual Throwable instance; it does not establish original JVM parity.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path

ANNOTATION = re.compile(r"@SneakyThrows(?:\([^)]*\))?")
IMPORT = re.compile(r"^import lombok\.SneakyThrows;\s*\n", re.M)
HELPER = """
    @SuppressWarnings("unchecked")
    private static <T extends Throwable> RuntimeException spkRecoverySneaky(Throwable error) throws T {
        throw (T) error;
    }
"""

def sha(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()

def advance(s: str, i: int) -> int:
    if s.startswith("//", i):
        p = s.find("\n", i + 2)
        return len(s) if p < 0 else p
    if s.startswith("/*", i):
        p = s.find("*/", i + 2)
        if p < 0: raise ValueError("Unterminated comment")
        return p + 2
    if s[i] in "\"'":
        quote, p = s[i], i + 1
        while p < len(s):
            if s[p] == "\\": p += 2; continue
            if s[p] == quote: return p + 1
            p += 1
        raise ValueError("Unterminated string")
    return i + 1

def body_start(s: str, i: int) -> int:
    depth = 0
    while i < len(s):
        if s[i] in "\"'" or s.startswith(("/*", "//"), i):
            i = advance(s, i); continue
        if s[i] == "(": depth += 1
        elif s[i] == ")": depth -= 1
        elif s[i] == "{" and depth == 0: return i
        elif s[i] == ";" and depth == 0: raise ValueError("No method body")
        i += 1
    raise ValueError("Method body not found")

def body_end(s: str, i: int) -> int:
    depth = 0
    while i < len(s):
        if s[i] in "\"'" or s.startswith(("/*", "//"), i):
            i = advance(s, i); continue
        if s[i] == "{": depth += 1
        elif s[i] == "}":
            depth -= 1
            if depth == 0: return i
        i += 1
    raise ValueError("Unbalanced braces")

def rewrite_java(original: str) -> tuple[str, int]:
    if "spkRecoverySneaky(" in original:
        raise ValueError("Helper name already exists")
    chunks, previous, count = [], 0, 0
    for match in ANNOTATION.finditer(original):
        start = body_start(original, match.end())
        stop = body_end(original, start)
        if match.start() < previous:
            raise ValueError("Nested annotations unsupported")
        chunks += [original[previous:match.start()], original[match.end():start],
                   "{\n        try {\n", original[start + 1:stop],
                   "\n        } catch (Throwable spkRecoveryFailure) {\n"
                   "            throw spkRecoverySneaky(spkRecoveryFailure);\n"
                   "        }\n    }"]
        previous, count = stop + 1, count + 1
    if not count: return original, 0
    chunks.append(original[previous:])
    result = IMPORT.sub("", "".join(chunks))
    position = result.rfind("}")
    if position < 0: raise ValueError("No class ending")
    return result[:position] + HELPER + result[position:], count

def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source-zip", type=Path, required=True)
    p.add_argument("--allowlist", type=Path, required=True,
                   help="JSON mapping of source-relative filename to expected input SHA-256")
    p.add_argument("--out-zip", type=Path, required=True)
    args = p.parse_args()
    expected = json.loads(args.allowlist.read_text(encoding="utf-8"))
    if not isinstance(expected, dict) or not expected:
        raise ValueError("Nonempty reviewed allowlist required")
    updated, report = {}, {}
    with zipfile.ZipFile(args.source_zip) as source:
        members = source.namelist()
        if len(members) != len(set(members)):
            raise ValueError("Duplicate ZIP names")
        for path, digest in sorted(expected.items()):
            if (not path.startswith("src/") or not path.endswith(".java")
                    or ".." in Path(path).parts or "\\" in path):
                raise ValueError("Invalid Java source member path")
            if path not in members: raise ValueError("Missing source member " + path)
            before = source.read(path)
            if sha(before) != digest: raise ValueError("Stale source hash " + path)
            rewritten, methods = rewrite_java(before.decode("utf-8"))
            if not methods: raise ValueError("No annotated methods in " + path)
            updated[path] = rewritten.encode("utf-8")
            report[path] = {"old_sha256": sha(before), "new_sha256": sha(updated[path]),
                            "methods": methods}
        with zipfile.ZipFile(args.out_zip, mode="x", compression=zipfile.ZIP_DEFLATED) as target:
            for name in members:
                data = updated.get(name)
                if data is None: data = source.read(name)
                target.writestr(name, data)
            target.writestr("PRIVATE_R194_REWRITE.json", json.dumps(report, indent=2) + "\n")
    print(json.dumps({"changed_sources": len(report),
                      "rewritten_methods": sum(x["methods"] for x in report.values())}))

if __name__ == "__main__":
    main()

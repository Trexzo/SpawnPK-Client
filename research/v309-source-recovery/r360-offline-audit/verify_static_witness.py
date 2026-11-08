"""R350: fail-closed static witness for original v309 endpoint and cache paths.

Input: locally generated javap -c -p / -v -p transcripts, NOT Java source.
This does not execute the game, grant localhost access, or attest that arbitrary
supplied text was generated from the SHA-pinned JAR.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re

PIN = "ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38"
SIZE = 17532075

class WitnessRefused(ValueError):
    pass

def original_jar_admitted(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size != SIZE:
        raise WitnessRefused("PINNED_ORIGINAL_JAR_SIZE_OR_TYPE_MISMATCH")
    with path.open("rb") as f:
        digest = hashlib.file_digest(f, "sha256").hexdigest()
    if digest != PIN:
        raise WitnessRefused("PINNED_ORIGINAL_JAR_SHA256_MISMATCH")

def read_javap(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 12000000:
        raise WitnessRefused("INVALID_JAVAP_FILE")
    data = path.read_bytes()
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        s = data.decode("utf-16")
    else:
        s = data.decode("utf-8-sig")
    return s.replace("\r\n", "\n").replace("\r", "\n")

def section(src, header):
    lines = src.splitlines()
    matches = [i for i,l in enumerate(lines) if l.startswith("  ") and
               l.strip() == header]
    if len(matches) != 1:
        raise WitnessRefused("MISSING_OR_DUPLICATE_METHOD_" + header)
    i = matches[0]
    end = next((j for j in range(i+1,len(lines))
                if re.match(r"^  \S", lines[j])), len(lines))
    return "\n".join(lines[i:end])

def ordered(src, *parts):
    found = [src.find(x) for x in parts]
    if min(found) < 0 or found != sorted(found) or len(set(found)) != len(found):
        raise WitnessRefused("MISSING_OR_REORDERED_STATIC_WITNESS")

def bootstrap_recipe(verbose, number, recipe):
    if verbose.count("BootstrapMethods:") != 1:
        raise WitnessRefused("MISSING_OR_DUPLICATE_BOOTSTRAP_TABLE")
    block = verbose.split("BootstrapMethods:",1)[1].split("InnerClasses:",1)[0]
    match = re.search(r"(?m)^    " + str(number) +
                      r": .*?\n\s+Method arguments:\n\s+#\d+\s+([^\r\n]+)$",
                      block)
    if not match or match.group(1).strip() != recipe:
        raise WitnessRefused("BOOTSTRAP_RECIPE_MISMATCH_" + str(number))

def evaluate(enum_javap, settings_javap, dirs_javap, dirs_verbose, client_javap):
    enum_init = section(enum_javap, "static {};")
    ordered(enum_init, "String SPAWNPK", "String SpawnPK",
            'Field a:Lrs/f/a$a;')
    settings_init = section(settings_javap, "static {};")
    ordered(settings_init,
            'Field rs/f/a$a.a:Lrs/f/a$a;',
            'Field a:Lrs/f/a$a;',
            'Method rs/f/a$a.b:(Lrs/f/a$a;)Ljava/lang/String;',
            'Field B:Ljava/lang/String;')
    for header, invoke in (
        ("public static java.lang.String b();", "InvokeDynamic #3:makeConcatWithConstants"),
        ("public static java.lang.String f();", "InvokeDynamic #5:makeConcatWithConstants"),
    ):
        method = section(dirs_javap, header)
        ordered(method, "String user.home", "String file.separator",
                "Field rs/f/a.B:Ljava/lang/String;",
                "Method java/lang/String.toLowerCase:()Ljava/lang/String;",
                invoke, "java/io/File.mkdir:()Z")
        if "areturn" not in method:
            raise WitnessRefused("CACHE_PATH_RETURN_MISSING")
    bootstrap_recipe(dirs_verbose, 3, r".\u0001-data")
    bootstrap_recipe(dirs_verbose, 5, r".\u0001")
    socket = section(client_javap, "public java.net.Socket b(int);")
    ordered(socket, "class java/net/Socket",
            "String www.spawnpk.org",
            "Method java/net/InetAddress.getByName:(Ljava/lang/String;)Ljava/net/InetAddress;",
            "iload_1",
            'Method java/net/Socket."<init>":(Ljava/net/InetAddress;I)V')
    if "System.getProperty" in socket or "System.getenv" in socket:
        raise WitnessRefused("SOCKET_FACTORY_PROPERTY_FLOW_UNEXPECTED")
    port_sites = re.findall(
        r"(?m)^\s+\d+:\s+(?:ldc(?:_w)?|sipush)\s+.*?// int 43594\s*\n"
        r"\s+\d+:\s+invokevirtual\s+.*?// Method b:\(I\)Ljava/net/Socket;",
        client_javap)
    if len(port_sites) != 1:
        raise WitnessRefused("LOGIN_PORT_CALLSITE_NOT_UNIQUE")
    return {
        "status": "R350_STATIC_ORIGINAL_ENDPOINT_AND_CACHE_RESOLVED",
        "original_login_host_in_socket_method": "www.spawnpk.org",
        "original_login_port_literal": 43594,
        "original_socket_method_reads_spk_properties": False,
        "data_directory_suffix": ".spawnpk-data",
        "cache_directory_suffix": ".spawnpk",
        "owner_local_cache_identity_approved_for_r328": False,
        "real_original_jar_execution_by_this_verifier": False,
        "arbitrary_javap_text_provenance_attested": False,
        "original_client_localhost_connection": "NOT_TESTED",
        "authenticated_original_login": "NOT_TESTED",
        "same_process_reconnect": "NOT_TESTED",
        "inventory_revision_recovery": "NOT_TESTED",
    }

def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("original-jar", "enum-javap", "settings-javap", "dirs-javap",
                 "dirs-verbose-javap", "client-javap"):
        p.add_argument("--"+name, required=True, type=Path)
    a = p.parse_args()
    try:
        original_jar_admitted(a.original_jar)
        result = evaluate(*(read_javap(getattr(a, x)) for x in (
            "enum_javap", "settings_javap", "dirs_javap",
            "dirs_verbose_javap", "client_javap")))
    except (OSError, UnicodeError, WitnessRefused) as e:
        print(json.dumps({"status":"R350_STATIC_WITNESS_REFUSED",
                          "reason":str(e),"same_process_reconnect":"NOT_TESTED"}))
        return 2
    result["original_jar_sha256"] = PIN
    result["jar_sha_pinned_but_text_provenance_not_attested"] = True
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

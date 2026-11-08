"""R348 static v309 cache-path and socket-callsite evidence gate.

Accepts installed-JDK javap -c -p TEXT. Never launches the game.
Original JAR SHA must be verified separately. A port-callsite does not prove
a server hostname, property override, authentication, or reconnect.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ORIGINAL_SHA="ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38"
ORIGINAL_SIZE=17532075
MAX_JAVAP_BYTES=12000000

class EvidenceRefused(ValueError):
    pass

def validate_original_jar(path):
    f=Path(path)
    if f.is_symlink() or not f.is_file() or f.stat().st_size!=ORIGINAL_SIZE:
        raise EvidenceRefused("ORIGINAL_JAR_SIZE_OR_TYPE_MISMATCH")
    h=hashlib.sha256()
    with f.open("rb") as stream:
        for chunk in iter(lambda:stream.read(1<<20),b""):
            h.update(chunk)
    if h.hexdigest()!=ORIGINAL_SHA:
        raise EvidenceRefused("ORIGINAL_JAR_SHA256_MISMATCH")
    return True

def decode_javap(path):
    p=Path(path)
    if p.is_symlink() or not p.is_file() or p.stat().st_size>MAX_JAVAP_BYTES:
        raise EvidenceRefused("UNTRUSTED_JAVAP_TEXT_FILE")
    raw=p.read_bytes()
    if raw.startswith((b"\xff\xfe",b"\xfe\xff")):
        text=raw.decode("utf-16")
    elif raw.startswith(b"\xef\xbb\xbf"):
        text=raw.decode("utf-8-sig")
    else:
        text=raw.decode("utf-8")
    return text.replace("\r\n","\n").replace("\r","\n")

def method_section(text,pattern):
    lines=text.splitlines()
    headers=[i for i,l in enumerate(lines)
             if re.match(r"^  \S",l) and re.fullmatch(pattern,l.strip())]
    if len(headers)!=1:
        raise EvidenceRefused("EXPECTED_ONE_METHOD_"+str(len(headers)))
    start=headers[0]
    end=next((i for i in range(start+1,len(lines))
              if re.match(r"^  \S",lines[i]) and not lines[i].strip().startswith(
                  ("Code:","Exception table:","LineNumberTable:","LocalVariableTable:"))),
             len(lines))
    return "\n".join(lines[start:end])

def audit_cache_path(text):
    method=method_section(text,r"public static java\.lang\.String b\(\);")
    ordered=[
        "String user.home",
        "String file.separator",
        "Field rs/f/a.B:Ljava/lang/String;",
        "Method java/lang/String.toLowerCase:()Ljava/lang/String;",
    ]
    positions=[]
    for part in ordered:
        at=method.find(part)
        if at<0:
            raise EvidenceRefused("CACHE_PATH_WITNESS_MISSING_"+part.split()[0])
        positions.append(at)
    if positions!=sorted(positions):
        raise EvidenceRefused("CACHE_PATH_WITNESS_ORDER_CHANGED")
    if "java/io/File.mkdir" not in method or not re.search(r"\bareturn\b",method):
        raise EvidenceRefused("CACHE_DIRECTORY_CREATION_OR_RETURN_MISSING")
    return {
        "status":"ORIGINAL_CACHE_PATH_FORMULA_WITNESSED",
        "user_home_property_used":True,
        "file_separator_property_used":True,
        "game_directory_field":"rs.f.a.B",
        "game_directory_lowercased":True,
        "concrete_cache_directory_name":"UNRESOLVED",
        "candidate_cache_location_authorized":False,
    }

def audit_socket_callsite(text):
    lines=text.splitlines()
    calls=[]
    for i,line in enumerate(lines):
        if re.search(r"(?<!\d)43594(?!\d)",line) and re.search(
            r"\b(?:sipush|ldc|ldc_w)\b",line):
            segment="\n".join(lines[i:i+24])
            if re.search(r"Method (?:rs/Client\.)?b:\(I\)Ljava/net/Socket;",segment):
                calls.append(i)
    if len(calls)!=1:
        raise EvidenceRefused("EXPECTED_ONE_LOGIN_SOCKET_PORT_CALLSITE_"+str(len(calls)))
    return {
        "status":"ORIGINAL_LOGIN_SOCKET_CALLSITE_WITNESSED",
        "observed_port_literal":43594,
        "called_original_method_signature":"rs.Client.b(int):java.net.Socket",
        "actual_remote_host":"UNRESOLVED",
        "spk_serverPort_override_works":"NOT_VERIFIED",
        "local_listener_receives_original_client":"NOT_TESTED",
    }

def audit_texts(cache_text,client_text):
    return {
        "status":"R348_STATIC_ORIGINAL_CLIENT_ENDPOINT_AND_CACHE_WITNESSES",
        "source":"JAVAP_TEXT_INPUT_NOT_RUNTIME",
        "original_jar_identity":"NOT_ATTESTED_BY_TEXT_ALONE",
        "cache_path":audit_cache_path(cache_text),
        "login_socket":audit_socket_callsite(client_text),
        "r347_loopback_is_protocol_compatible":False,
        "original_v309_authenticated_login":"NOT_TESTED",
        "original_same_process_reconnect":"NOT_TESTED",
        "original_inventory_recovery":"NOT_TESTED",
    }

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cache-javap",type=Path,required=True)
    p.add_argument("--client-javap",type=Path,required=True)
    p.add_argument("--original-jar",type=Path)
    args=p.parse_args(argv)
    try:
        if args.original_jar is None:
            raise EvidenceRefused("REAL_ORIGINAL_JAR_PROVENANCE_REQUIRED")
        validate_original_jar(args.original_jar)
        report=audit_texts(decode_javap(args.cache_javap),
                           decode_javap(args.client_javap))
        report["original_jar_identity"]="JAR_SHA_PINNED_BUT_TEXT_PROVENANCE_UNATTESTED"
        report["status"]="R348_ORIGINAL_JAR_PINNED_STATIC_WITNESSES_ONLY"
    except (OSError,UnicodeError,EvidenceRefused) as exc:
        print(json.dumps({
            "status":"R348_BYTECODE_WITNESS_BLOCKED",
            "reason":str(exc),
            "original_same_process_reconnect":"NOT_TESTED",
        }))
        return 2
    print(json.dumps(report,sort_keys=True,indent=2))
    return 0

if __name__=="__main__":
    sys.exit(main())

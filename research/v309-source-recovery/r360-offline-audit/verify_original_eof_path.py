"""R338 — offline fail-closed static witness for original v309 EOF/reconnect path.

Requires SHA256-pinned *original* 17.5MB v309 JAR and locally generated
`javap -c -p` text for rs.Client and rs.q.b. Never runs game, decompiles,
uploads binaries, nor proves a reconnect occurred at runtime.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ORIGINAL_SHA256 = "ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38"
ORIGINAL_LENGTH = 17532075
HEAD = re.compile(
    r"(?m)^  (?:(?:public|private|protected|static|final|synchronized|native|abstract)\s+)+"
    r"[^\r\n]+\([^\r\n]*\);[ \t]*\r?$"
)

class WitnessBlocked(ValueError):
    pass

def sha256_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for part in iter(lambda:f.read(1<<20), b""):
            h.update(part)
    return h.hexdigest()

def extract_method(disassembly, signature):
    starts = list(HEAD.finditer(disassembly))
    targets = [i for i,m in enumerate(starts)
               if m.group(0).strip().rstrip("\r") == signature]
    if len(targets)!=1:
        raise WitnessBlocked("METHOD_NOT_UNIQUELY_FOUND_"+signature)
    i=targets[0]
    start=starts[i].end()
    end=starts[i+1].start() if i+1<len(starts) else len(disassembly)
    body=disassembly[start:end]
    if "    Code:" not in body:
        raise WitnessBlocked("METHOD_WITHOUT_BYTECODE_"+signature)
    return body

def require(text, fragment, reason):
    if fragment not in text:
        raise WitnessBlocked(reason)

def require_regex(text, regex, reason):
    if re.search(regex, text, flags=re.M) is None:
        raise WitnessBlocked(reason)

def trace_disassembly(client_disasm, worker_disasm):
    """Report only the conditions really observable in authentic javap."""
    login=extract_method(client_disasm,
        "public void a(java.lang.String, java.lang.String, boolean);")
    reconnect=extract_method(client_disasm,"public void x();")
    poll=extract_method(client_disasm,"private boolean bP();")
    tick=extract_method(client_disasm,"private void bz();")
    outbound=extract_method(client_disasm,"public void a(rs.o.a.a.a);")
    available=extract_method(worker_disasm,"public int c();")
    read=extract_method(worker_disasm,"public void a(byte[], int);")
    close=extract_method(worker_disasm,"public void a();")

    require(login, "String Please wait patiently while we attempt to reconnect",
            "MISSING_LOGIN_RECONNECT_UI_CONTEXT")
    require(login, "Method b:(I)Ljava/net/Socket;",
            "MISSING_LOGIN_SOCKET_CREATION")
    require(login, "Method rs/q/b.\"<init>\":(Lrs/C;Ljava/net/Socket;)V",
            "MISSING_NEW_SOCKET_WORKER")
    require(login, "String Error connecting to server!",
            "MISSING_LOGIN_ERROR_HANDLER_UI")
    require_regex(login, r"\b2273:\s+astore", "LOGIN_HANDLER_CHANGED")
    require_regex(login,
        r"\b\d+\s+\d+\s+2273\s+Class java/io/IOException",
        "LOGIN_ERROR_HANDLER_NOT_IO_EXCEPTION")

    require(reconnect, "String Connection lost", "MISSING_DISCONNECT_CONTEXT")
    require(reconnect, "String Please wait - attempting to reestablish",
            "MISSING_RECONNECT_ATTEMPT_UI")
    require_regex(reconnect,
        r"\b1\d\d:\s+iconst_1\s*\n\s*1\d\d:\s+invokevirtual"
        r"\s+#[0-9]+\s+// Method a:\(Ljava/lang/String;Ljava/lang/String;Z\)V",
        "RECONNECT_NOT_CALLING_LOGIN_WITH_TRUE")
    require_regex(reconnect,
        r"\b\d+:\s+getfield\s+#[0-9]+\s+// Field nF:Lrs/q/b;",
        "RECONNECT_NOT_RETAINING_OLD_WORKER")
    require(reconnect,"Method rs/q/b.a:()V","RECONNECT_NOT_CLOSING_OLD_WORKER")
    if reconnect.index("Method a:(Ljava/lang/String;Ljava/lang/String;Z)V") > reconnect.index("Method rs/q/b.a:()V"):
        raise WitnessBlocked("OLD_SOCKET_CLOSED_BEFORE_RELOGIN")

    require(poll,"Method rs/q/b.c:()I","POLL_NOT_QUERYING_AVAILABLE")
    require_regex(poll,
        r"\b1[78]:\s+ifne\s+23\s*\n\s*21:\s+iconst_0\s*\n\s*22:\s+ireturn",
        "ZERO_AVAILABLE_DOES_NOT_EARLY_RETURN")
    require(poll,"Method rs/q/b.a:([BI)V","POLL_NOT_READING_FRAMED_BODY")
    require_regex(poll,
        r"\b213:\s+iload_1\s*\n\s*214:\s+aload_0[\s\S]{0,170}"
        r"\b218:\s+if_icmpge\s+223\s*\n\s*221:\s+iconst_0\s*\n\s*222:\s+ireturn",
        "SHORT_FRAME_NO_LONGER_RETURNS_WITHOUT_READ")
    require_regex(poll,
        r"18231:\s+astore_1[\s\S]{0,160}\b18233:\s+invokevirtual"
        r"\s+#[0-9]+\s+// Method x:\(\)V",
        "INBOUND_IO_EXCEPTION_DOES_NOT_CALL_RECONNECT")
    require_regex(poll,
        r"\b\d+\s+\d+\s+18231\s+Class java/io/IOException",
        "INBOUND_IO_EXCEPTION_CATCH_NOT_PINNED")

    require(tick,"Method bP:()Z","GAME_TICK_NOT_CALLING_PACKET_POLLER")
    require(tick,"bipush        100","GAME_TICK_LIMIT_NOT_PINNED")
    require(outbound,"Method x:()V","OUTBOUND_IO_FAILURE_NOT_CALLING_RECONNECT")
    require_regex(outbound,
        r"\b\d+\s+\d+\s+69\s+Class java/io/IOException",
        "OUTBOUND_IO_CATCH_CHANGED")

    require(available,"Method java/io/InputStream.available:()I",
            "SOCKET_AVAILABLE_NOT_USING_STREAM_AVAILABLE")
    require(read,"Method java/io/InputStream.read:([BII)I",
            "SOCKET_BODY_READ_NOT_PRESENT")
    require(read,"String EOF","SOCKET_EOF_EXCEPTION_NOT_PRESENT")
    require(read,"class java/io/IOException","SOCKET_EOF_NOT_IO_EXCEPTION")
    require(close,"Method java/net/Socket.close:()V",
            "SOCKET_WORKER_NO_LONGER_CLOSES_SOCKET")

    return {
        "status":"ORIGINAL_V309_STATIC_RECONNECT_PATH_VERIFIED_ONLY",
        "same_client_object_relogin_call":"PRESENT_IN_BYTECODE",
        "old_socket_worker_close":"PRESENT_AFTER_RELOGIN_CALL",
        "inbound_ioexception_to_reconnect":"PRESENT_IN_BYTECODE",
        "outbound_ioexception_to_reconnect":"PRESENT_IN_BYTECODE",
        "game_tick_polls_inbound_packets":"PRESENT_IN_BYTECODE",
        "zero_available_early_return":"PRESENT_IN_BYTECODE",
        "short_frame_early_return":"PRESENT_IN_BYTECODE",
        "possible_eof_detection_gap":"SHORT_FRAME_MAY_NOT_ATTEMPT_READ_AND_THUS_NOT_THROW_EOF",
        "actual_original_v309_auto_reconnect":"NOT_TESTED",
        "actual_original_v309_opcode53_recovery":"NOT_TESTED",
        "dynamic_socket_pid_capture":"NOT_PERFORMED"
    }

def read_javap_text(path):
    """Decode PowerShell 5 UTF-16 and normalize platform-dependent newlines."""
    raw=Path(path).read_bytes()
    if raw.startswith((bytes.fromhex("fffe"),bytes.fromhex("feff"))):
        result=raw.decode("utf-16")
    elif raw.startswith(bytes.fromhex("efbbbf")):
        result=raw.decode("utf-8-sig")
    elif 0 in raw:
        raise WitnessBlocked("UNMARKED_BINARY_OR_UNSUPPORTED_JAVAP_ENCODING")
    else:
        result=raw.decode("utf-8")
    return result.replace(chr(13)+chr(10),chr(10)).replace(chr(13),chr(10))

def inspect_files(jar,client,worker):
    jar=Path(jar)
    if not jar.is_file() or jar.is_symlink() or jar.stat().st_size!=ORIGINAL_LENGTH:
        raise WitnessBlocked("ORIGINAL_V309_JAR_NOT_ADMITTED")
    if sha256_file(jar)!=ORIGINAL_SHA256:
        raise WitnessBlocked("ORIGINAL_V309_SHA256_MISMATCH")
    return trace_disassembly(
        read_javap_text(client),
        read_javap_text(worker)
    )

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--jar",type=Path,required=True)
    p.add_argument("--client-javap",type=Path,required=True)
    p.add_argument("--worker-javap",type=Path,required=True)
    p.add_argument("--report",type=Path)
    args=p.parse_args(argv)
    try:
        result=inspect_files(args.jar,args.client_javap,args.worker_javap)
    except (OSError,ValueError,UnicodeError,WitnessBlocked) as e:
        print(json.dumps({"status":"BLOCKED","reason":str(e),
                          "actual_original_v309_auto_reconnect":"NOT_TESTED"}))
        return 2
    out=json.dumps(result,indent=2,sort_keys=True)+"\n"
    if args.report:
        args.report.write_text(out,encoding="utf-8")
    print(out)
    return 0

if __name__=="__main__":
    sys.exit(main())

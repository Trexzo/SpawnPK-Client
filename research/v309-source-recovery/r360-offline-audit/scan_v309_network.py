#!/usr/bin/env python3
"""R355: read-only, pinned-JAR static bytecode audit. No original code executes.

Only prints known networking API method references seen in real JVM invocation
instructions. Never prints arbitrary original constant strings, URLs or logs.
This is NOT a runtime network trace or a substitute for OS egress isolation.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from collections import deque
import struct
import zipfile
from pathlib import Path
from typing import Iterator

PIN = "ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38"
PIN_SIZE = 17_532_075
MAX_CLASSES = 50_000
MAX_CLASS_BYTES = 8 * 1024 * 1024
MAX_UNCOMPRESSED = 512 * 1024 * 1024
MAX_REPORT_ROWS = 15_000

class AuditRefused(ValueError):
    pass

class Reader:
    def __init__(self, data: bytes):
        self.data = data
        self.at = 0
    def take(self, n: int) -> bytes:
        if n < 0 or self.at + n > len(self.data):
            raise AuditRefused("MALFORMED_CLASSFILE_BOUNDS")
        b = self.data[self.at:self.at+n]
        self.at += n
        return b
    def u1(self) -> int:
        return self.take(1)[0]
    def u2(self) -> int:
        return struct.unpack(">H", self.take(2))[0]
    def u4(self) -> int:
        return struct.unpack(">I", self.take(4))[0]

# Fixed bytecode widths. Unlisted JVM opcodes have width 1; reject invalid ones.
WIDTHS = {op:2 for op in (0x10, 0x12, *range(0x15,0x1a), *range(0x36,0x3b), 0xa9, 0xbc)}
WIDTHS.update({op:3 for op in (0x11,0x13,0x14,0x84,*range(0x99,0xa9),
                                  *range(0xb2,0xb9),0xbb,0xbd,0xc0,0xc1,0xc6,0xc7)})
WIDTHS.update({0xb9:5,0xba:5,0xc5:4,0xc8:5,0xc9:5})
MAX_OPCODE = 0xc9

# Include HTTP stacks and low-level socket APIs, including third-party owners.
API_PREFIXES = (
    "java/net/", "javax/net/", "java/net/http/", "java/nio/channels/SocketChannel",
    "java/nio/channels/DatagramChannel", "org/apache/http/", "okhttp3/",
    "com/squareup/okhttp/", "io/netty/channel/socket/", "sun/net/www/",
)
# java/net has benign address/URI helpers; exclude most non-network plumbing.
API_OWNER_NAMES = {
    "Socket", "SocketImpl", "ServerSocket", "DatagramSocket", "DatagramPacket",
    "InetAddress", "InetSocketAddress", "URL", "URLConnection", "HttpURLConnection",
    "HttpsURLConnection", "HttpCookie", "Proxy", "ProxySelector", "Authenticator",
    "NetworkInterface", "MulticastSocket", "SocketAddress", "URLEncoder", "URLDecoder",
    "SocketTimeoutException", "UnknownHostException", "SSLSocket", "SSLSocketFactory",
    "SSLContext", "SSLServerSocket", "SSLServerSocketFactory",
}
REFLECTIVE_CALLS = {
    ("java/lang/Class", "forName"), ("java/lang/reflect/Method", "invoke"),
    ("java/lang/reflect/Constructor", "newInstance"),
}
STARTUP_CLASSES = {"rs/gui/Launcher", "rs/p/a", "rs/gui/M", "rs/s/g", "rs/ui/f", "rs/A/q"}

def interesting(owner: str) -> bool:
    if owner.startswith("java/net/") or owner.startswith("javax/net/"):
        return owner.split("/")[-1].split("$")[0] in API_OWNER_NAMES or owner.startswith("java/net/http/")
    return owner.startswith(API_PREFIXES[3:])

def bytecode_ops(code: bytes) -> Iterator[tuple[int,int,int|None]]:
    """Decode opcodes and constant-pool operands, handling switches and wide."""
    pos = 0
    n = len(code)
    while pos < n:
        op = code[pos]
        if op > MAX_OPCODE or op in (0xca,):
            raise AuditRefused("INVALID_JVM_OPCODE")
        idx = None
        if op == 0xaa:  # tableswitch
            base = pos + 1 + ((-(pos + 1)) % 4)
            if base+12 > n: raise AuditRefused("MALFORMED_TABLESWITCH")
            lo, hi = struct.unpack_from(">ii",code,base+4)
            count = hi-lo+1
            if count < 0 or count > (n//4) or base+12+count*4 > n:
                raise AuditRefused("MALFORMED_TABLESWITCH")
            new_pos = base+12+count*4
        elif op == 0xab:  # lookupswitch
            base = pos+1+((-(pos+1))%4)
            if base+8 > n: raise AuditRefused("MALFORMED_LOOKUPSWITCH")
            count = struct.unpack_from(">i",code,base+4)[0]
            if count < 0 or count > n//8 or base+8+count*8 > n:
                raise AuditRefused("MALFORMED_LOOKUPSWITCH")
            new_pos=base+8+count*8
        elif op == 0xc4:  # wide
            if pos+2 > n: raise AuditRefused("MALFORMED_WIDE")
            next_op=code[pos+1]
            if next_op == 0x84: new_pos=pos+6
            elif next_op in (*range(0x15,0x1a), *range(0x36,0x3b), 0xa9): new_pos=pos+4
            else: raise AuditRefused("MALFORMED_WIDE")
            if new_pos>n: raise AuditRefused("MALFORMED_WIDE")
        else:
            width=WIDTHS.get(op,1)
            new_pos=pos+width
            if new_pos>n: raise AuditRefused("TRUNCATED_OPCODE")
            if op in (0xb6,0xb7,0xb8,0xb9,0xba):
                idx=struct.unpack_from(">H",code,pos+1)[0]
        yield pos,op,idx
        pos=new_pos
    if pos!=n: raise AuditRefused("BAD_OPCODE_ALIGNMENT")

def parse_class(raw:bytes) -> tuple[str,list[dict],int,list[tuple]]:
    r=Reader(raw)
    if r.u4()!=0xCAFEBABE: raise AuditRefused("BAD_CLASS_MAGIC")
    minor=r.u2(); major=r.u2()
    if not 45<=major<=65: raise AuditRefused("UNSUPPORTED_CLASS_VERSION")
    cp_count=r.u2()
    cp=[None]*cp_count
    ix=1
    while ix<cp_count:
        tag=r.u1()
        if tag == 1:
            size=r.u2();cp[ix]=(1,r.take(size).decode("utf-8",errors="replace"))
        elif tag in (3,4): r.take(4);cp[ix]=(tag,)
        elif tag in (5,6): r.take(8);cp[ix]=(tag,);ix+=1
        elif tag in (7,8,16,19,20):cp[ix]=(tag,r.u2())
        elif tag in (9,10,11,12,17,18):cp[ix]=(tag,r.u2(),r.u2())
        elif tag == 15:cp[ix]=(tag,r.u1(),r.u2())
        else: raise AuditRefused("UNKNOWN_CP_TAG")
        ix+=1
    def entry(i:int,kind:int|None=None):
        if i<1 or i>=cp_count or cp[i] is None or (kind is not None and cp[i][0]!=kind):
            raise AuditRefused("BAD_CP_INDEX")
        return cp[i]
    def utf(i:int)->str:return entry(i,1)[1]
    r.u2() # flags
    this=r.u2()
    class_name=utf(entry(this,7)[1])
    r.u2() # superclass
    interfaces=r.u2()
    r.take(interfaces*2)
    def skip_attributes():
        count=r.u2()
        for _ in range(count):r.u2();r.take(r.u4())
    for _ in range(r.u2()):
        r.take(6);skip_attributes()  # fields
    observations=[]
    internal_edges=[]
    indirect=0
    for _ in range(r.u2()):
        r.u2() # method flags
        method=utf(r.u2()); descriptor=utf(r.u2())
        for _ in range(r.u2()):
            attr=utf(r.u2());length=r.u4();sub=Reader(r.take(length))
            if attr!="Code":continue
            sub.u2();sub.u2();code=sub.take(sub.u4())
            for off,op,index in bytecode_ops(code):
                if op == 0xba:
                    indirect+=1
                    continue
                if index is None:continue
                ref=entry(index)
                if ref[0] not in (10,11):raise AuditRefused("INVOKE_NOT_METHOD_REF")
                owner=utf(entry(ref[1],7)[1])
                names=entry(ref[2],12)
                target=utf(names[1]); signature=utf(names[2])
                if owner.startswith("rs/"):
                    internal_edges.append(((class_name,method,descriptor),(owner,target,signature)))
                if interesting(owner):
                    observations.append({
                        "class":class_name.replace("/","."),"method":method,
                        "method_descriptor":descriptor,"bytecode_offset":off,
                        "opcode":f"0x{op:02x}","target_class":owner.replace("/","."),
                        "target_method":target,"target_descriptor":signature,
                    })
                elif (owner,target) in REFLECTIVE_CALLS:
                    indirect+=1
            sub.take(sub.u2()*8) # exception table
            for _ in range(sub.u2()):sub.u2();sub.take(sub.u4())
            if sub.at!=len(sub.data):raise AuditRefused("CODE_ATTRIBUTE_TRAILING_DATA")
    skip_attributes() # class attrs
    if r.at!=len(raw): raise AuditRefused("CLASS_TRAILING_DATA")
    return class_name, observations, indirect, internal_edges

def audit_jar(jar:Path,*,expected_pin=PIN,expected_size=PIN_SIZE)->dict:
    jar=Path(jar)
    if jar.is_symlink() or not jar.is_file():raise AuditRefused("MISSING_OR_SYMLINK_JAR")
    if jar.stat().st_size!=expected_size:raise AuditRefused("ORIGINAL_JAR_SIZE_MISMATCH")
    with jar.open("rb") as f:
        h=hashlib.file_digest(f,"sha256").hexdigest()
    if h!=expected_pin:raise AuditRefused("ORIGINAL_JAR_SHA256_MISMATCH")
    rows=[]
    class_count=0;network_classes=set(); indirect_classes=set(); indirect_count=0
    internal_graph={}; root_nodes=set()
    with zipfile.ZipFile(jar,"r") as z:
        infos=z.infolist()
        if len(infos)>100_000:raise AuditRefused("TOO_MANY_ARCHIVE_ENTRIES")
        if len({i.filename for i in infos}) != len(infos):
            raise AuditRefused("DUPLICATE_ARCHIVE_ENTRIES")
        first_party=[i for i in infos if i.filename.startswith("rs/") and i.filename.endswith(".class")]
        if len(first_party)>MAX_CLASSES:raise AuditRefused("TOO_MANY_FIRST_PARTY_CLASSES")
        if sum(i.file_size for i in infos)>MAX_UNCOMPRESSED:raise AuditRefused("ZIP_EXPANSION_TOO_LARGE")
        for info in first_party:
            if info.file_size>MAX_CLASS_BYTES:raise AuditRefused("OVERSIZED_CLASS")
            klass, calls, ind, internal_edges=parse_class(z.read(info))
            if klass+".class" != info.filename:
                raise AuditRefused("CLASS_ENTRY_NAME_MISMATCH")
            class_count+=1
            for caller,target in internal_edges:
                internal_graph.setdefault(caller,set()).add(target)
            if klass=="rs/gui/Launcher":
                # Root methods are identified through the incoming caller edge.
                # If main contains no rs/ calls, this remains intentionally empty.
                root_nodes.update(a for a,b in internal_edges if a[1]=="main")
            if calls:network_classes.add(klass.replace("/","."))
            if ind:indirect_classes.add(klass.replace("/","."))
            indirect_count+=ind
            rows.extend(calls)
            if len(rows)>MAX_REPORT_ROWS:raise AuditRefused("REPORT_ROW_LIMIT_EXCEEDED")
    rows.sort(key=lambda v:(v["class"],v["method"],v["bytecode_offset"],v["target_class"]))
    # Heuristic only: nominal first-party calls from Launcher.main. Does not
    # model dynamic dispatch, class initialization, Guice, native or reflection.
    hop_limit=12
    distance={node:0 for node in root_nodes}
    previous={node:None for node in root_nodes}
    queue=deque(root_nodes)
    while queue:
        node=queue.popleft()
        if distance[node]>=hop_limit:continue
        for target in sorted(internal_graph.get(node,())):
            if target not in distance:
                distance[target]=distance[node]+1
                previous[target]=node
                queue.append(target)
    def path_to(node):
        chain=[]
        while node is not None:
            chain.append(node[0].replace("/",".")+"#"+node[1]+node[2])
            node=previous[node]
        return list(reversed(chain))
    reachable=[]
    for row in rows:
        node=(row["class"].replace(".","/"),row["method"],row["method_descriptor"])
        if node in distance:
            reachable.append({"class":row["class"],"method":row["method"],
               "target_class":row["target_class"],"target_method":row["target_method"],
               "nominal_hops_from_launcher_main":distance[node],
               "path":path_to(node)})
    startup_hits=[r for r in rows if r["class"].replace(".","/") in STARTUP_CLASSES]
    original_client=[r for r in rows if r["class"]=="rs.Client" and r["method"]=="b"]
    baseline_hosts=any(r["target_class"]=="java.net.InetAddress" and r["target_method"]=="getByName" for r in original_client)
    baseline_socket=any(r["target_class"]=="java.net.Socket" and r["target_method"]=="<init>" for r in original_client)
    return {
        "schema":"R355_ORIGINAL_V309_NETWORK_BYTECODE_INVOKES_V1",
        "original_jar_sha256":h,"original_jar_bytes":expected_size,
        "scope":"rs/ classes only; method-level direct invocation instructions",
        "original_jar_executed":False,"os_egress_attested":False,
        "runtime_network_destinations_verified":False,
        "login_verified":False,"same_pid_reconnect_verified":False,
        "classes_scanned":class_count,
        "network_invocations_count":len(rows),
        "network_calling_classes_count":len(network_classes),
        "indirect_invocation_or_reflection_count":indirect_count,
        "indirect_calling_classes_count":len(indirect_classes),
        "known_client_b_getByName_seen":baseline_hosts,
        "known_client_b_socket_init_seen":baseline_socket,
        "startup_class_network_callsite_count":len(startup_hits),
        "nominal_launcher_main_roots":len(root_nodes),
        "nominal_startup_reachable_network_calls_count":len(reachable),
        "nominal_startup_paths_truncated":len(reachable)>100,
        "nominal_startup_network_paths":reachable[:100],
        "nominal_startup_path_hop_limit":hop_limit,
        "network_calls":rows,
    }

def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--jar",required=True,type=Path,help="verified owner original v309 client.jar")
    p.add_argument("--out",required=True,type=Path,help="new JSON report OUTSIDE original JAR directory")
    args=p.parse_args(argv)
    try:
        if args.jar.is_symlink():raise AuditRefused("SYMLINK_JAR_REFUSED")
        jar=args.jar.resolve(strict=True)
        out=args.out
        if out.is_symlink() or out.exists():raise AuditRefused("OUTPUT_ALREADY_EXISTS_OR_SYMLINK")
        destination=out.resolve(strict=False)
        if jar.parent==destination.parent or jar.parent in destination.parents:
            raise AuditRefused("OUTPUT_INSIDE_ORIGINAL_DIRECTORY")
        if not destination.parent.is_dir():raise AuditRefused("OUTPUT_PARENT_MISSING")
        result=audit_jar(jar)
        with destination.open("x",encoding="utf-8") as f:
            json.dump(result,f,indent=2,sort_keys=True)
            f.write("\n")
        print(json.dumps({"status":"R355_STATIC_AUDIT_COMPLETE","sha256":result["original_jar_sha256"],
             "classes_scanned":result["classes_scanned"],"network_callsite_count":result["network_invocations_count"],
             "original_client_executed":False,"report":str(destination)}))
        return 0
    except (AuditRefused, ValueError, OSError, zipfile.BadZipFile) as ex:
        print(json.dumps({"status":"R355_REFUSED","reason":str(ex)}))
        return 2

if __name__=="__main__":
    raise SystemExit(main())

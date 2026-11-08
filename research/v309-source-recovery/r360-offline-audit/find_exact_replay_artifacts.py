"""R343: inspect owner-local paths and ZIP backup members for exact R315/R328 artifacts.

Read-only and no archive extraction. Every accepted artifact requires both byte
length and SHA-256; cache directory counts are discovery clues, NEVER approved
R328 corpus provenance. Can scan loose files and one ZIP layer.

Use separate --root and --archive arguments; --out is the only optional write.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
import stat
import sys
import zipfile

PINS = {
    "ORIGINAL_V309_GAME_JAR": (17532075,
        "ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38"),
    "R315_REBUILT_CLASS_ONLY_JAR": (2516277,
        "b551c58e7e07154f1a5b27e153db9df803bbbca820cc8ee133e8b515aba72721"),
    "R328_PRIVATE_GUI_SERVER_FIXTURE_ZIP": (675506,
        "79e3aea38f2177bb799da9b750ac4597c1c3a7618e2ccfc7ab18e5fb518d38f8"),
    "R315_FULL_SOURCE_ZIP": (24339390,
        "e46a213ba949dc0a2f420a040b5c9d38451c0923e3ea39917a5d2eb3c9b2fa28"),
}
SIZES = {size for size, _ in PINS.values()}
REFERENCE_CACHE_COUNT = 10772
EXCLUDED_DIRS = frozenset({
    ".git", "node_modules", "credentials", "secrets", "tokens", "accounts",
    "passwords", "cookies", "sessions", "browser-profile", "browser_profiles",
})
MAX_FILES = 400000
MAX_ZIP_ENTRIES = 350000
MAX_CANDIDATE_BYTES = 800 * 1024 * 1024
MAX_CANDIDATES = 1800

class ScanRefused(ValueError):
    pass

def member_path(name):
    clean=name.replace("\\", "/")
    segments=clean.split("/")
    if (clean.startswith("/") or not clean or any(
        not s or s=="." or s==".." for s in segments
    ) or (len(segments[0])>1 and segments[0][1]==":")):
        return None
    if any(s.casefold() in EXCLUDED_DIRS for s in segments[:-1]):
        return None
    return clean

def checked_sha256(stream, size):
    digest=hashlib.sha256()
    observed=0
    while True:
        chunk=stream.read(1024 * 1024)
        if not chunk:break
        observed+=len(chunk)
        if observed>size:raise ScanRefused("STREAM_LONGER_THAN_MEMBER_SIZE")
        digest.update(chunk)
    if observed!=size:raise ScanRefused("TRUNCATED_MEMBER")
    return digest.hexdigest()

def matching_artifacts(byte_size, digest, source):
    return [
        {"artifact": name, "locator": source, "size": byte_size,
         "sha256": expected}
        for name, (size, expected) in PINS.items()
        if size==byte_size and expected==digest
    ]

def cache_prefix(clean):
    pieces=clean.split("/")
    # Indexed using the subtree prefix (e.g. backup/2026/cache), not the file.
    for i, part in enumerate(pieces[:-1]):
        if part.casefold() in ("cache", "assetcache", "jagexcache"):
            if i+2<=len(pieces):
                return "/".join(pieces[:i+1])
    return None

def bounded_candidate(used_bytes, candidates, size, *, max_bytes):
    if candidates>=MAX_CANDIDATES or used_bytes+size>max_bytes:
        raise ScanRefused("CANDIDATE_HASH_BUDGET_EXCEEDED")

def scan_zip(path, *, max_entries=MAX_ZIP_ENTRIES,
             max_candidate_bytes=MAX_CANDIDATE_BYTES):
    archive=Path(path)
    if archive.is_symlink() or not archive.is_file():
        raise ScanRefused("ARCHIVE_MISSING_OR_SYMLINK")
    out={"kind":"ZIP","path":str(archive),"status":"COMPLETE",
         "entry_count":0,"files_considered":0,"candidate_hashed":0,
         "candidate_bytes_hashed":0,"matched_artifacts":[],
         "cache_subtrees":[],"unreadable_candidate_count":0,
         "original_client_launched":False}
    cache=defaultdict(lambda:{"count":0,"total_bytes":0,"names":set()})
    with zipfile.ZipFile(archive) as z:
        for info in z.infolist():
            out["entry_count"]+=1
            if out["entry_count"]>max_entries:
                out["status"]="INCOMPLETE_ENTRY_BUDGET"
                break
            if info.is_dir():continue
            clean=member_path(info.filename)
            if clean is None:continue
            # Unix symlink in zip central directory; never follow it.
            mode=(info.external_attr>>16)&0xffff
            if stat.S_IFMT(mode)==stat.S_IFLNK:
                out["status"]="INCOMPLETE_UNSAFE_ZIP_MEMBER"
                continue
            if info.flag_bits & 0x1:
                out["status"]="INCOMPLETE_ENCRYPTED_MEMBER"
                continue
            out["files_considered"]+=1
            prefix=cache_prefix(clean)
            if prefix is not None:
                key=clean[len(prefix)+1:]
                group=cache[prefix]
                if key in group["names"]:
                    out["status"]="INCOMPLETE_DUPLICATE_CACHE_ENTRY"
                else:
                    group["names"].add(key)
                    group["count"]+=1
                    group["total_bytes"]+=info.file_size
            if info.file_size not in SIZES:continue
            try:
                bounded_candidate(
                    out["candidate_bytes_hashed"],out["candidate_hashed"],
                    info.file_size,max_bytes=max_candidate_bytes)
                # A highly compressed member could be a compression bomb;
                # reject rather than opening uncertain input.
                ratio=(info.file_size / max(1,info.compress_size))
                if ratio>500:
                    out["status"]="INCOMPLETE_SUSPICIOUS_ZIP_COMPRESSION"
                    continue
                with z.open(info) as stream:
                    digest=checked_sha256(stream,info.file_size)
                out["candidate_hashed"]+=1
                out["candidate_bytes_hashed"]+=info.file_size
                out["matched_artifacts"]+=matching_artifacts(
                    info.file_size,digest,str(archive)+"::"+clean)
            except (ScanRefused, OSError, RuntimeError, zipfile.BadZipFile, EOFError):
                out["unreadable_candidate_count"]+=1
                out["status"]="INCOMPLETE_CANDIDATE"
                # No false complete assertion; continue to return partial leads.
                continue
    # Only display plausible cache subtrees, even if their provenance differs.
    ranked=sorted(cache.items(),key=lambda x:(
        abs(x[1]["count"]-REFERENCE_CACHE_COUNT),-x[1]["count"],x[0]))
    out["cache_subtrees"]=[
        {"prefix":name,"file_count":data["count"],
         "total_bytes":data["total_bytes"],
         "count_matches_R328":data["count"]==REFERENCE_CACHE_COUNT,
         "approved_R328_cache_provenance":False}
        for name,data in ranked[:25]
    ]
    return out

def scan_directory(root, *, max_files=MAX_FILES,
                   max_candidate_bytes=MAX_CANDIDATE_BYTES):
    root=Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ScanRefused("ROOT_MISSING_OR_SYMLINK")
    out={"kind":"DIRECTORY","path":str(root),"status":"COMPLETE",
         "file_count":0,"candidate_hashed":0,"candidate_bytes_hashed":0,
         "matched_artifacts":[],"original_client_launched":False}
    # rglob doesn't normally follow symlink directories, but mark incomplete.
    for file in root.rglob("*"):
        if file.is_symlink():
            out["status"]="INCOMPLETE_SYMLINK"
            continue
        if file.is_dir():continue
        if not file.is_file():
            out["status"]="INCOMPLETE_SPECIAL_FILE"
            continue
        rel=member_path(file.relative_to(root).as_posix())
        if rel is None:continue
        out["file_count"]+=1
        if out["file_count"]>max_files:
            out["status"]="INCOMPLETE_FILE_BUDGET"
            break
        size=file.stat().st_size
        if size not in SIZES:continue
        try:
            bounded_candidate(out["candidate_bytes_hashed"],
                out["candidate_hashed"],size,max_bytes=max_candidate_bytes)
            with file.open("rb") as handle:
                digest=checked_sha256(handle,size)
            out["candidate_hashed"]+=1
            out["candidate_bytes_hashed"]+=size
            out["matched_artifacts"]+=matching_artifacts(
                size,digest,str(file))
        except (ScanRefused,OSError):
            out["status"]="INCOMPLETE_CANDIDATE"
    return out

def combine(reports):
    hits=[]
    for report in reports:
        hits.extend(report["matched_artifacts"])
    verified=sorted({hit["artifact"] for hit in hits})
    needed={"R328_PRIVATE_GUI_SERVER_FIXTURE_ZIP",
            "R315_REBUILT_CLASS_ONLY_JAR"}
    return {
        "status":"COMPLETE" if all(x["status"]=="COMPLETE" for x in reports)
                 else "PARTIAL",
        "verified_artifact_names":verified,
        "verified_artifact_locations":hits,
        "R328_built_jar_and_fixture_found":needed.issubset(verified),
        "approved_R328_cache_verified":False,
        "original_same_pid_reconnect":"NOT_TESTED",
        "original_client_launched":False,
        "reports":reports
    }

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root",type=Path,action="append",default=[])
    p.add_argument("--archive",type=Path,action="append",default=[])
    p.add_argument("--max-entries",type=int,default=MAX_ZIP_ENTRIES)
    p.add_argument("--max-files",type=int,default=MAX_FILES)
    p.add_argument("--out",type=Path)
    args=p.parse_args(argv)
    if not args.root and not args.archive:
        p.error("provide at least one --root or --archive")
    try:
        if args.max_entries<=0 or args.max_files<=0:
            raise ScanRefused("INVALID_ENTRY_BUDGET")
        reports=[scan_directory(root,max_files=args.max_files)
                 for root in args.root]
        reports += [scan_zip(path,max_entries=args.max_entries)
                    for path in args.archive]
        result=combine(reports)
        output=json.dumps(result,indent=2,sort_keys=True)+"\n"
        if args.out:
            args.out.write_text(output,encoding="utf-8")
        print(output)
        return 0 if result["status"]=="COMPLETE" else 3
    except (ScanRefused,OSError,ValueError,zipfile.BadZipFile) as exc:
        print(json.dumps({"status":"BLOCKED","reason":str(exc),
                          "original_same_pid_reconnect":"NOT_TESTED"}))
        return 2

if __name__=="__main__":
    sys.exit(main())

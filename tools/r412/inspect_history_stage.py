#!/usr/bin/env python3
"""R412 non-destructive inspect-only inventory of one EXPLICIT history directory.

Only filename/type/size metadata are read by default. With --hash, SHA256
reads are permitted exclusively for bounded regular files on systems with
O_NOFOLLOW. Never prints source bytes, JSON records, full paths or usernames.
Never deletes, moves, truncates, edits, or guesses recovery authority.
Never silently chooses "main" versus "stage"; no journal exists here.

No implicit default directory: caller must select it explicitly. Safe to
run against user-created synthetic TEMP fixtures; this script's tests do not
need any private or production paths.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys

MAX_BYTES=64*1024*1024
TARGETS=("loot-history.json","loot-history.json.tmp")

def _kind(mode:int)->str:
    if stat.S_ISREG(mode):return "REGULAR"
    if stat.S_ISLNK(mode):return "SYMLINK"
    if stat.S_ISDIR(mode):return "DIRECTORY"
    return "NONREGULAR"

def _hash_nofollow(path:Path,before:os.stat_result,limit:int)->dict:
    # An ordinary open on Windows may follow a reparse point even if
    # lstat previously showed a regular file. Fail closed instead.
    nofollow=getattr(os,"O_NOFOLLOW",None)
    if nofollow is None:
        return {"hash_status":"UNAVAILABLE_NO_NOFOLLOW"}
    fd=None
    try:
        flags=os.O_RDONLY|nofollow|getattr(os,"O_CLOEXEC",0)|getattr(os,"O_NONBLOCK",0)
        fd=os.open(path,flags)
        actual=os.fstat(fd)
        if not stat.S_ISREG(actual.st_mode):
            return {"hash_status":"REFUSED_NOT_REGULAR"}
        key=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)
        if key(actual)!=key(before):
            return {"hash_status":"REFUSED_CHANGED_BEFORE_OPEN"}
        if actual.st_size>limit:
            return {"hash_status":"REFUSED_TOO_LARGE"}
        dig=hashlib.sha256()
        count=0
        while True:
            chunk=os.read(fd,min(1024*1024,limit+1-count))
            if not chunk:break
            count+=len(chunk)
            if count>limit:
                return {"hash_status":"REFUSED_CHANGED_OR_OVERSIZE"}
            dig.update(chunk)
            if count==limit:
                if os.read(fd,1):
                    return {"hash_status":"REFUSED_CHANGED_OR_OVERSIZE"}
                break
        after_fd=os.fstat(fd)
        after_path=os.lstat(path)
        if key(after_fd)!=key(before) or key(after_path)!=key(before) or count!=before.st_size:
            return {"hash_status":"REFUSED_CHANGED_DURING_READ"}
        return {"hash_status":"SHA256_OK","sha256":dig.hexdigest()}
    except (OSError,PermissionError):
        return {"hash_status":"REFUSED_IO_OR_RACE"}
    finally:
        if fd is not None:os.close(fd)

def _entry(directory:Path,name:str,hash_requested:bool,limit:int)->dict:
    result={"file":name}
    path=directory/name
    try:
        st=os.lstat(path)
    except FileNotFoundError:
        result["status"]="ABSENT"
        return result
    except (OSError,PermissionError):
        result["status"]="UNREADABLE"
        return result
    result["status"]=_kind(st.st_mode)
    if result["status"]!="REGULAR":
        return result
    result["size_bytes"]=st.st_size
    if st.st_size>limit:
        result["status"]="OVERSIZED"
        return result
    if hash_requested:
        result.update(_hash_nofollow(path,st,limit))
    return result

def inspect(directory:Path,hash_requested:bool=False,max_bytes:int=MAX_BYTES)->dict:
    if max_bytes<1 or max_bytes>MAX_BYTES:
        raise ValueError("R412_INVALID_SIZE_CAP")
    # Do not canonicalize with resolve(): following a directory symlink
    # outside the explicitly requested workspace is forbidden.
    try:
        root_st=os.lstat(directory)
    except OSError as e:
        raise ValueError("R412_DIRECTORY_NOT_ACCESSIBLE") from e
    if not stat.S_ISDIR(root_st.st_mode):
        raise ValueError("R412_DIRECTORY_NOT_REAL_DIRECTORY")
    entries=[_entry(directory,n,hash_requested,max_bytes) for n in TARGETS]
    main,stage=entries
    stage_state=("CLEAR" if stage["status"]=="ABSENT" else
                 "ORPHAN" if stage["status"] in ("REGULAR","OVERSIZED") else
                 "UNSAFE")
    if stage_state!="CLEAR":
        verdict="QUARANTINED_REQUIRES_EXPLICIT_RECONCILIATION"
    elif main["status"] in ("ABSENT","REGULAR"):
        verdict="NO_STAGE_OBSERVED_NO_RECOVERY_PROOF"
    else:
        verdict="UNSAFE_MAIN_FILE"
    return {
        "status":"R412_READ_ONLY_INSPECTION",
        "mode":"HASH_NOFOLLOW" if hash_requested else "METADATA_ONLY",
        "directory_name_exposed":False,
        "entries":entries,
        "stage_state":stage_state,
        "conclusion":verdict,
        "automatic_recovery_permitted":False,
        "main_file_authoritative_proven":False,
        "stage_file_authoritative_proven":False,
        "files_modified":False,
        "file_contents_displayed":False,
        "cross_process_stability_proven":False,
    }

def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--directory",required=True,type=Path,
                   help="Explicitly authorized directory; no default")
    p.add_argument("--hash",action="store_true",
                   help="Opt in to bounded regular-file SHA256 reads where no-follow is supported")
    p.add_argument("--max-bytes",type=int,default=MAX_BYTES,
                   help="Per-file cap; maximum 67108864 bytes")
    a=p.parse_args(argv)
    try:
        result=inspect(a.directory,hash_requested=a.hash,max_bytes=a.max_bytes)
        print(json.dumps(result,sort_keys=True,indent=2))
        return 0
    except ValueError as e:
        print(json.dumps({"status":"R412_INSPECTION_REFUSED","reason":str(e)}))
        return 2

if __name__=="__main__":
    sys.exit(main())

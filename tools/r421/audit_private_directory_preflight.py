#!/usr/bin/env python3
"""R421 read-only exact SHA-pinned audit of private TEMP-only path-preflight delta.

Never prints private source/class bytes, opens player history, runs the client,
creates directories, touches v312 or authorizes release. Structure-only, NOT a
race-free security proof against hostile concurrent path replacement.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re

STORE = "rs/plugins/loottracker/LootHistoryStore.java"
PLUGIN = "rs/plugins/loottracker/LootTrackerPlugin.java"
CHANGED = {STORE, PLUGIN}
CLASS = lambda p: p[:-5]+".class"


class Refused(RuntimeError):
    pass


def need(ok: bool, why: str):
    if not ok:
        raise Refused(why)


def inventory(root: Path, suffix: str) -> dict[str, str]:
    need(root.is_dir() and not root.is_symlink(), "INVALID_INPUT_TREE")
    items = {}
    for path in root.rglob("*"+suffix):
        need(path.is_file() and not path.is_symlink(), "UNSAFE_INPUT_MEMBER")
        relative = path.relative_to(root).as_posix()
        need(relative not in items, "DUPLICATE_FILE")
        items[relative] = sha256(path.read_bytes()).hexdigest()
    return items


def clean(source: str) -> str:
    return re.sub(r"/\*[\s\S]*?\*/|//[^\n]*", " ", source)


def method(source: str, name: str) -> str:
    m = re.search(r"\b"+re.escape(name)+r"\s*\([^;{}]*\)\s*(?:throws\s+[\w, ]+\s*)?\{",source)
    need(m is not None, "MISSING_"+name)
    start=source.index("{",m.start())
    level=0
    for i in range(start,len(source)):
        if source[i]=="{":
            level+=1
        elif source[i]=="}":
            level-=1
            if level==0:
                return source[start+1:i]
    raise Refused("UNBALANCED_"+name)


def in_order(source: str, *parts: str) -> bool:
    position=0
    for part in parts:
        location=source.find(part,position)
        if location<0:
            return False
        position=location+len(part)
    return True


def check(source_store: str, source_plugin: str,
          prior_store: str, prior_plugin: str) -> dict:
    old_s, old_p = clean(prior_store), clean(prior_plugin)
    s,p=clean(source_store),clean(source_plugin)
    need("r421PrepareHistoryDirectoryForLease(" not in old_s and
         "r421CacheLocationWithoutCreation(" not in old_s and
         "r421PrepareHistoryDirectoryForLease(" not in old_p,
         "R421_ALREADY_PRESENT_IN_PRIOR")
    constructor=method(s,"LootHistoryStore")
    resolver=method(s,"r421CacheLocationWithoutCreation")
    prepare=method(s,"r421PrepareHistoryDirectoryForLease")
    identity=method(s,"r421SameDirectoryIdentity")
    worker_retry=method(p,"r420AcquireRestoreLeaseWithBoundedRetry")
    restore=method(p,"loadHistory")

    need(s.count("r421CacheLocationWithoutCreation(")==2 and
         "this(r421CacheLocationWithoutCreation())" in constructor,
         "R421_CONSTRUCTOR_MUST_USE_NONMUTATING_RESOLVER")
    need("Class307.method121()" not in s,
         "R421_UPSTREAM_UNGUARDED_MKDIR_STILL_IN_STORE")
    need("Configuration.field1268" in resolver and
         '"[A-Za-z0-9_-]{1,80}"' in resolver and
         "Configuration.field1256" in resolver and
         "Configuration.isTestBuild" in resolver and
         "System.getProperty(\"user.home\")" in resolver and
         'return "." + File.separator + "cache" + File.separator;' in resolver,
         "R421_CACHE_ORIGIN_OR_VERSION_PATH_DRIFT")
    need("throw new IllegalStateException" in resolver and
         "key == null" in resolver and
         "home == null" in resolver,
         "R421_UNSAFE_OR_NULL_PATH_MUST_REFUSE")
    need(s.count("r421PrepareHistoryDirectoryForLease(")==1 and
         p.count("r421PrepareHistoryDirectoryForLease(")==1,
         "R421_PREPARE_MUST_HAVE_SINGLE_BACKGROUND_CALL")
    need(in_order(prepare, "final File parentFile = file.getParentFile()",
                  "parentFile.toPath().toAbsolutePath().normalize()",
                  "directory.getParent()", "while (ancestor != null)",
                  "Files.readAttributes(", "LinkOption.NOFOLLOW_LINKS",
                  "Files.createDirectory(directory)"),
         "R421_NOFOLLOW_PARENT_CHECK_MUST_PRECEDE_CREATE")
    for token in ("parentBefore", "parentAfter", "leafBefore", "leafAfter",
                  "FileAlreadyExistsException collision",
                  "NoSuchFileException absent", "r421SameDirectoryIdentity(",
                  "isSymbolicLink()", "isOther()", "SecurityException"):
        need(token in prepare, "R421_MISSING_PREPARE_GUARD_"+token)
    need(prepare.count("Files.createDirectory(directory)") == 1,
         "R421_MORE_THAN_ONE_DIRECTORY_CREATE")
    need("before.fileKey().equals(after.fileKey())" in identity and
         "before.isDirectory()" in identity and
         "!before.isSymbolicLink()" in identity,
         "R421_PARENT_OR_LEAF_IDENTITY_WEAKENED")
    for forbidden in ("Files.createDirectories(", ".mkdirs(", ".mkdir(",
                      "Files.delete", "Files.move", "Files.copy",
                      "Files.newOutputStream", "Files.write", "Files.createLink",
                      "FileChannel.open("):
        need(forbidden not in prepare and forbidden not in resolver,
             "R421_FORBIDDEN_UNBOUNDED_SIDE_EFFECT_"+forbidden)
    need("SwingUtilities.isEventDispatchThread()" in worker_retry and
         "Thread.currentThread().isInterrupted()" in worker_retry,
         "R421_BACKGROUND_ONLY_OR_CANCEL_MISSING")
    need(in_order(worker_retry, "SwingUtilities.isEventDispatchThread()",
                  "synchronized (r395HistoryGate)",
                  "generation != r395HistoryGeneration",
                  "historyStore != restoreStore",
                  "restoreStore.r421PrepareHistoryDirectoryForLease()",
                  "final long[] retryDelayMillis",
                  "for (long delay : retryDelayMillis)",
                  "restoreStore.r419ActivateOwner()"),
         "R421_DIR_PREP_MUST_FOLLOW_SESSION_CHECK_AND_PRECEDE_LOCK")
    need("restoreStore.r421PrepareHistoryDirectoryForLease()" not in restore and
         "r420AcquireRestoreLeaseWithBoundedRetry(restoreStore, generation)" in restore,
         "R421_DIR_PREP_MUST_NOT_BE_DIRECT_EDT_RESTORE_CALL")
    return {
        "noncreating_store_constructor":True,
        "same_configuration_cache_path":True,
        "bounded_one_level_directory_creation":True,
        "ancestor_and_leaf_nofollow_preflight":True,
        "collision_and_unknown_paths_fail_closed":True,
        "per_session_background_only_preparation":True,
        "journals_unchanged":True,
        "hostile_path_swap_not_proved_safe":True,
    }


def audit(prior_src: Path, candidate_src: Path,
          prior_cls: Path, candidate_cls: Path,
          pins: dict[str,str], source_count=1277, class_count=1394) -> dict:
    a,b=inventory(prior_src,".java"),inventory(candidate_src,".java")
    c,d=inventory(prior_cls,".class"),inventory(candidate_cls,".class")
    need(len(a)==len(b)==source_count and a.keys()==b.keys(),"SOURCE_INVENTORY_DRIFT")
    need(len(c)==len(d)==class_count and c.keys()==d.keys(),"CLASS_INVENTORY_DRIFT")
    need({k for k in a if a[k]!=b[k]}==CHANGED,"NOT_EXACT_TWO_PRIVATE_SOURCES")
    need({k for k in c if c[k]!=d[k]}=={CLASS(k) for k in CHANGED},
         "NOT_EXACT_TWO_PRIVATE_CLASSES")
    for key,actual in (("prior-store",a[STORE]),("new-store",b[STORE]),
                       ("prior-plugin",a[PLUGIN]),("new-plugin",b[PLUGIN])):
        pin=pins[key]
        need(re.fullmatch("[0-9a-f]{64}",pin) is not None and actual==pin,
             "PRIVATE_SOURCE_SHA_PIN_DRIFT_"+key)
    properties=check((candidate_src/STORE).read_text("utf8"),
                     (candidate_src/PLUGIN).read_text("utf8"),
                     (prior_src/STORE).read_text("utf8"),
                     (prior_src/PLUGIN).read_text("utf8"))
    return {
        "status":"R421_OWNER_TEMP_DIRECTORY_PREFLIGHT_STATIC_GATE_PASS",
        "source_count":len(b),
        "compiled_classes":len(d),
        "modified_sources":2,
        "modified_existing_classes":2,
        **properties,
        "private_game_executed":False,
        "real_history_opened":False,
        "release_authorized":False,
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ("prior-sources","candidate-sources","prior-classes","candidate-classes"):
        p.add_argument("--"+n,type=Path,required=True)
    for n in ("prior-store","new-store","prior-plugin","new-plugin"):
        p.add_argument("--"+n+"-sha256",required=True)
    x=p.parse_args()
    pins={n:getattr(x,n.replace("-","_")+"_sha256")
          for n in ("prior-store","new-store","prior-plugin","new-plugin")}
    try:
        result=audit(x.prior_sources,x.candidate_sources,
                     x.prior_classes,x.candidate_classes,pins)
        print(json.dumps(result,sort_keys=True))
        return 0
    except (Refused,OSError,ValueError,UnicodeError,KeyError) as e:
        print(json.dumps({"status":"R421_REFUSED",
                          "reason":str(e) if isinstance(e,Refused) else "INVALID_INPUT"}))
        return 2

if __name__=="__main__":
    raise SystemExit(main())

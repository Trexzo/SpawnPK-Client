#!/usr/bin/env python3
"""Public-only structural gate for R415's independent invented Java model.

This program does not read or emit recovered private Java, classfiles,
history, credentials, real markers, or a user filesystem. It checks that
the *synthetic test protocol* still exercises fail-closed nonclobber
intent production and does not silently auto-acknowledge a deletion.

Passing this gate is NOT proof that the actual private client was patched,
compiled, tested, executed or can be safely installed. R415 private audit
and release are explicitly not authorized by this public fixture.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re

EXPECTED="R415NonClobberDeleteIntentSynthetic.java"

class Refused(ValueError):
    pass

def need(s:str,t:str,reason:str)->None:
    if t not in s:raise Refused(reason)

def order(s:str,*tokens:str)->None:
    cursor=0
    for token in tokens:
        found=s.find(token,cursor)
        if found<0:raise Refused("R415_SYNTHETIC_ORDER_DRIFT_"+token[:38])
        cursor=found+len(token)

def body(s:str,signature:str)->str:
    pos=s.find(signature)
    if pos<0:raise Refused("R415_SYNTHETIC_METHOD_MISSING_"+signature)
    begin=s.find("{",pos)
    if begin<0:raise Refused("R415_SYNTHETIC_BRACE_MISSING")
    depth=0
    # This is source-structure smoke testing, not a full Java parser.
    # Exact known fixture shapes are validated with additional checks.
    for i in range(begin,len(s)):
        if s[i]=="{":depth+=1
        elif s[i]=="}":
            depth-=1
            if depth==0:return s[begin+1:i]
    raise Refused("R415_SYNTHETIC_UNBALANCED_BRACE")

def inspect(source:str)->dict:
    for token in (
        "enum Phase {NOT_ATTEMPTED,FAILED_BEFORE_REPLACE,REPLACE_ATTEMPTED,COMMITTED}",
        "enum State {NONE,ABORTED_BEFORE_REPLACE,COMMITTED_BEFORE_ACK,QUARANTINED}",
        "AFTER_STAGE_FORCE","AFTER_INTENT_FORCE","AFTER_HARDLINK",
        "AFTER_INTENT_TEMP_REMOVAL","AFTER_HISTORY_REPLACEMENT",
        "FOREIGN_MARKER_AFTER_PREFLIGHT","HISTORY_CHANGED_AFTER_INTENT",
        "STAGE_CHANGED_AFTER_INTENT","ATOMIC_MOVE_UNSUPPORTED",
        "System.exit(73)","R415_CHILD_COMMITTED_BEFORE_ACK_PASS",
        "R415_SYNTHETIC_NONCLOBBER_INTENT_PASS",
    ):need(source,token,"R415_SYNTHETIC_MISSING_SAFETY_CASE_"+token)
    main=body(source,"boolean delete22()throws IOException")
    if "if(phase!=Phase.COMMITTED)" in main or "if(!acknowledged)panel.clear()" in main:
        raise Refused("R415_AMBIGUOUS_WRITE_ROLLBACK_NOT_ALLOWED")
    order(main,
        "if(unsafe||!admitted())",
        "List<Integer> snapshot=new ArrayList<>(panel)",
        "panel.remove(Integer.valueOf(22))",
        "phase=Phase.FAILED_BEFORE_REPLACE",
        "result=writeConfirmed(currentPanelImage())",
        "acknowledged=result",
        "if(!result)",
        "unsafe=true",
        "if(phase==Phase.FAILED_BEFORE_REPLACE)",
        "panel.clear();panel.addAll(snapshot)",
        "else{",
        "unsafe=true")
    # A failed COMMITTED/REPLACE_ATTEMPTED write must NEVER cause an
    # optimistic UI rollback merely because its receipt is false.
    if "if(phase!=Phase.COMMITTED)" in main or "if(!acknowledged)panel.clear()" in main:
        raise Refused("R415_AMBIGUOUS_WRITE_ROLLBACK_NOT_ALLOWED")
    write=body(source,"boolean writeConfirmed(byte[] next)throws IOException")
    if re.search(r"Files\.move\s*\(\s*markerTemp\s*,\s*marker",write):
        raise Refused("R415_MARKER_OVERWRITE_BY_ATOMIC_MOVE_NOT_ALLOWED")
    if "if(after==null||before.equals(after))return false;" not in write:
        raise Refused("R415_EQUAL_BEFORE_AFTER_IMAGE_NOT_REFUSED")
    if write.count("before.equals(digest(history,true))")!=2 or \
       write.count("after.equals(digest(stage,false))")!=2:
        raise Refused("R415_PRE_AND_POST_PUBLICATION_REHASH_REQUIRED")
    after_publish=write.split("Files.delete(markerTemp)",1)
    if len(after_publish)!=2:
        raise Refused("R415_MARKER_TEMP_CLEANUP_MISSING")
    before_history_move=after_publish[1].split("phase=Phase.REPLACE_ATTEMPTED",1)[0]
    if "before.equals(digest(history,true))" not in before_history_move or \
       "after.equals(digest(stage,false))" not in before_history_move:
        raise Refused("R415_IMAGE_REHASH_MUST_FOLLOW_MARKER_PUBLICATION")
    order(write,
        "String before=digest(history,true)",
        "forced(stage,next)",
        "String after=digest(stage,false)",
        "forced(markerTemp,markerBytes)",
        "before.equals(digest(history,true))",
        "after.equals(digest(stage,false))",
        "Files.createLink(marker,markerTemp)",
        "Files.delete(markerTemp)",
        "eq(classify(),State.ABORTED_BEFORE_REPLACE",
        "phase=Phase.REPLACE_ATTEMPTED",
        "historyMoveAttempts++",
        "Files.move(stage,history,StandardCopyOption.ATOMIC_MOVE",
        "phase=Phase.COMMITTED")
    if re.search(r"Files\.move\s*\(\s*markerTemp\s*,\s*marker",write):
        raise Refused("R415_MARKER_OVERWRITE_BY_ATOMIC_MOVE_NOT_ALLOWED")
    if "StandardCopyOption.REPLACE_EXISTING" in write[
         write.index("Files.createLink(marker,markerTemp)"):
         write.index("Files.delete(markerTemp)")]:
        raise Refused("R415_INTENT_PUBLISH_CAN_OVERWRITE")
    if "Files.delete(marker)" in write or "Files.deleteIfExists(marker)" in write:
        raise Refused("R415_NEVER_AUTO_CLEAN_FINAL_INTENT")
    if write.count("forced(markerTemp,markerBytes)")!=1 or \
       write.count("Files.createLink(marker,markerTemp)")!=1:
        raise Refused("R415_INTENT_FORCE_OR_LINK_DUPLICATION")
    classification=body(source,"State classify()")
    order(classification,
        "if(present(markerTemp))return State.QUARANTINED",
        "if(!present(marker))return State.NONE",
        "LinkOption.NOFOLLOW_LINKS",
        "meta.size()>512",
        '"v=1"',
        'before=(ABSENT|[0-9a-f]{64})',
        'after=[0-9a-f]{64}',
        "String observed=digest(history,true)",
        "if(observed.equals(before))return State.ABORTED_BEFORE_REPLACE",
        "if(observed.equals(after))return State.COMMITTED_BEFORE_ACK",
        "return State.QUARANTINED")
    admission=body(source,"boolean admitted()")
    need(admission,"classify()==State.NONE&&!present(stage)",
         "R415_SECOND_DELETE_NOT_FENCED")
    if "Files.delete(marker)" in classification or "Files.delete(marker)" in admission:
        raise Refused("R415_CLASSIFICATION_NOT_READ_ONLY")
    for test in (
        "cleanConfirmedCommit", "secondDeleteBlocked",
        "earlierMarkerRefusesDeletion", "foreignMarkerAfterPreflightNotOverwritten",
        "crashAfterIntentTempForceIsQuarantined",
        "crashAfterHardlinkQuarantinesBothNames",
        "crashAfterIntentPublishedClassifiesAborted",
        "crashAfterHistoryMoveRecognizedOnRestart",
        "unsupportedAtomicHistoryMoveStaysAmbiguous",
        "mainChangedAfterMarkerRefusesMove",
        "stagedChangedAfterMarkerRefusesMove",
        "separateJvmRestartCommittedBeforeAck",
    ):
        need(source,test+"();","R415_REQUIRED_SYNTHETIC_CASE_NOT_EXECUTED_"+test)
    return {
        "status":"R415_PUBLIC_ONLY_NONCLOBBER_SYNTHETIC_GATE_PASS",
        "stage_force_precedes_intent_force":True,
        "intent_publication_uses_exclusive_hardlink":True,
        "final_marker_auto_cleanup":False,
        "postmove_exception_auto_rollback":False,
        "second_delete_accepted_before_reconciliation":False,
        "history_replacement_must_be_strict_atomic":True,
        "fresh_jvm_restart_covered":True,
        "actual_private_candidate_verified":False,
        "private_game_executed":False,
        "production_history_inspected":False,
        "directory_metadata_durability_proven":False,
        "interprocess_lock_proven":False,
        "release_authorized":False,
        "merge_approved":False,
    }

def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--fixture",type=Path,required=True)
    a=p.parse_args(argv)
    try:
        if a.fixture.name!=EXPECTED or not a.fixture.is_file() or a.fixture.is_symlink():
            raise Refused("R415_EXPECTED_PUBLIC_FIXTURE_REQUIRED")
        report=inspect(a.fixture.read_text(encoding="utf8"))
        print(json.dumps(report,sort_keys=True,indent=2))
        return 0
    except (OSError,UnicodeError,Refused) as e:
        print(json.dumps({"status":"R415_PUBLIC_SYNTHETIC_REFUSED",
                          "reason":str(e) if isinstance(e,Refused) else "UNAVAILABLE_OR_UNTRUSTED_FILE"}))
        return 2
if __name__=="__main__":
    raise SystemExit(main())

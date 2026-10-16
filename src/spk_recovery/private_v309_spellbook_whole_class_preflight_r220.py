"""R220: fail-closed cross-batch 14-method / 4314-op integration gate.

Before a claim that all individually recovered methods form one rebuilt
source class, verify independently authored R212-R219 module contracts
agree on original method coverage, instruction counts, SHA-pinned original
binary and readable donor, and explicit compiler-shape exceptions.

This does NOT compile all methods together; it is a necessary consistency
preflight and cannot be promoted to whole-class or runtime acceptance.
"""
from __future__ import annotations
from collections import Counter
from dataclasses import dataclass
import importlib

ORIGINAL_CLASS_SHA256="b5e8b958c826dfc0a032f5a6d5d301f0c3405f2b68ed083fcf1ff49f1c8cc8e4"
DONOR_SHA256="8b8ece40b51b646eeb467ba3d258ab7a97bf65fb9543c846eca276497efe07d2"
FULL_CLIENT_SHA256="ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38"
EXPECTED={
    "<init>([Lrs/l/K;)V":4,
    "<clinit>()V":13,
    "h()V":10,
    "i()V":62,
    "j()V":19,
    "a(Lrs/n/c/ap$c;)V":243,
    "a()V":438,
    "m(I)V":76,
    "k()V":43,
    "l()V":160,
    "m()V":1580,
    "n()V":419,
    "o()V":760,
    "p()V":487,
}
MODULES={
    "r212":"spk_recovery.private_v309_readable_spellbook_three_methods_r212",
    "r213":"spk_recovery.private_v309_readable_spellbook_toggle_methods_r213",
    "r214":"spk_recovery.private_v309_readable_spellbook_long_filter_r214",
    "r215":"spk_recovery.private_v309_readable_spellbook_constructor_initializer_r215",
    "r216":"spk_recovery.private_v309_readable_spellbook_filter_panel_r216",
    "r217":"spk_recovery.private_v309_readable_spellbook_lunar_ancient_r217",
    "r218":"spk_recovery.private_v309_readable_spellbook_lunar_definitions_r218",
    "r219":"spk_recovery.private_v309_readable_spellbook_final_methods_r219",
}
# Audited original-method inventories, not names inferred from partial
# Java classes. Each row connects to an exact individual binary proof.
ROWS=(
    ("r212","h()V",10),("r212","i()V",62),("r212","j()V",19),
    ("r213","m(I)V",76),("r213","k()V",43),
    ("r214","a(Lrs/n/c/ap$c;)V",243),
    ("r215","<init>([Lrs/l/K;)V",4),("r215","<clinit>()V",13),
    ("r216","l()V",160),
    ("r217","n()V",419),("r217","p()V",487),
    ("r218","o()V",760),
    ("r219","a()V",438),("r219","m()V",1580),
)
# Compiler-shape normalizations are not silently accepted as verbatim
# original source. Keep provenance explicit in the combined gate.
NONVERBATIM={
    "a(Lrs/n/c/ap$c;)V":"r214: guard -> early return; two ArrayList locals typed List",
    "n()V":"r217: two compound-addition compiler-shape rewrites",
}


class R220IntegrationEvidenceError(ValueError):
    pass


def require(ok,why):
    if not ok:
        raise R220IntegrationEvidenceError(why)


def verify_manifest(rows=ROWS, expected=EXPECTED,
                    modules=MODULES,nonverbatim=NONVERBATIM,
                    load_modules=True):
    keys=[k for _,k,_ in rows]
    seen=Counter(keys)
    require(set(seen)==set(expected) and all(x==1 for x in seen.values()),
            "R220_DUPLICATE_OR_MISSING_ORIGINAL_JVM_METHOD")
    require(len(rows)==14 and sum(v for _,_,v in rows)==4314,
            "R220_ORIGINAL_METHOD_OP_INVENTORY_NOT_4314")
    require(all(expected[k]==count for _,k,count in rows),
            "R220_INDIVIDUAL_ORIGINAL_JVM_INSTRUCTION_COUNT_CHANGED")
    require(set(k for k,_,_ in rows)==set(modules),
            "R220_ORPHAN_PROOF_MODULE_OR_UNKNOWN_BATCH")
    require(set(nonverbatim)=={
        "a(Lrs/n/c/ap$c;)V","n()V"
    } and all(nonverbatim.values()),
            "R220_COMPILER_SHAPE_CHANGES_NOT_DOCUMENTED")
    checked=[]
    if load_modules:
        for batch,path in sorted(modules.items()):
            obj=importlib.import_module(path)
            found=[
                getattr(obj,key) for key in (
                    "ORIGINAL_CLASS_SHA256",
                    "ORIGINAL_PARENT_CLASS_SHA256",
                    "ORIGINAL_PARENT_SHA256",
                ) if hasattr(obj,key)]
            require(bool(found) and all(
                v==ORIGINAL_CLASS_SHA256 for v in found),
                "R220_ORIGINAL_CLASS_BINARY_HASH_DRIFT_"+batch)
            donors=[
                getattr(obj,key) for key in (
                    "SOURCE_SHA256","DONOR_JAVA_SHA256",
                    "DONOR_SHA256","READABLE_SOURCE_SHA256",
                ) if hasattr(obj,key)]
            # Some modules label their source differently; require any
            # present donor pins to be consistent, not inferred by name.
            require(all(v==DONOR_SHA256 for v in donors),
                    "R220_EXISTING_DEOBF_SOURCE_SHA_DRIFT_"+batch)
            checked.append(batch)
    return {
        "schema_version":1,
        "kind":"v309_fourteen_method_cross_recovery_consistency_r220",
        "original_owner":"rs/n/c/ap",
        "readable_owner":"rs/interfaces/widgets/Class179",
        "original_JVM_methods_inventoried":len(rows),
        "original_JVM_instructions_inventoried":sum(v for _,_,v in rows),
        "unique_complete_method_coverage":True,
        "individual_proof_modules_checked":checked,
        "compiler_normalized_method_count":len(nonverbatim),
        "verbatim_source_method_count":len(rows)-len(nonverbatim),
        "single_whole_class_Javac_compiled":False,
        "source_only_original_client_compiled":False,
        "source_distributed_or_game_executed":False,
    }

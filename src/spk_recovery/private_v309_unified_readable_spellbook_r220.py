"""R220: one-source-class ORIGINAL v309 spellbook JVM Code parity.

The same exact pre-existing decompiled Class179.java is rebuilt as ONE
14-method class using exactly five source compiler-shape edits already
proven in R214/R217 (3 filter, 2 ancient). All 4,314 original JVM
instructions, symbolic identity maps, and branch-target instruction
ordinals MUST agree in the single emitted readable Class179.class.
Exactly 178 ldc -> ldc_w encodings are allowed as constant-pool changes.

The separately assembled Java dependencies are explicitly NONORIGINAL
compiler signatures: this does not assert byte-identical original
classfiles, full client source closure or runtime correctness.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from zipfile import ZipFile

from .classfile import parse_class
from .private_client_namespace_legalizer_r125 import CANONICAL_V309
from .private_v309_readable_spellbook_long_filter_r214 import (
    extract_actual_donor_method,
    normalize_existing_method_for_original_javac,
    parse_javap_code,
)
from .private_v309_readable_spellbook_layouts_r217 import (
    extract_existing_method,
    normalize_ancient_compiler_shape,
)

ORIGINAL_CLASS_SHA256="b5e8b958c826dfc0a032f5a6d5d301f0c3405f2b68ed083fcf1ff49f1c8cc8e4"
SOURCE_TREE_SHA256="cabe0212e59bc7130e8d30548aa3bd23604ce2d019ad8ed879107c59001fdf0d"
EXISTING_READABLE_JAVA_SHA256="8b8ece40b51b646eeb467ba3d258ab7a97bf65fb9543c846eca276497efe07d2"
NORMALIZED_WHOLE_JAVA_SHA256="e274c0f12c36baeaa129920d5e259897a292b65a1138fc386f1413f00ff60406"
REFERENCE_SINGLE_COMPILED_CLASS_SHA256="b88820d9893b5a2d5b2ff05f5b88aa6d77dc5ee4a66f377db83758f1590c1c6e"
SOURCE_ENTRY="recovered-source/v309/src/rs/interfaces/widgets/Class179.java"
BRANCH_OPCODES=frozenset((
    "ifeq","ifne","iflt","ifge","ifgt","ifle",
    "if_icmpeq","if_icmpne","if_icmplt","if_icmpge",
    "if_icmpgt","if_icmple","if_acmpeq","if_acmpne",
    "ifnull","ifnonnull","goto","goto_w","jsr","jsr_w",
))
SYMBOL_PREFIXES=("Field ","Method ","InterfaceMethod ","class ","InvokeDynamic ")

# Method order is the ORIGINAL pinned classfile declaration order.
# Every digest pins the complete distinct symbolic alias table from the
# independent actual-original vs ONE unified normalized Java9 class replay.
METHOD_SPECS=(
    ("public static void h();","public static void method1966();",10,0,2,4,
     "c29bc71626d2926ce1c4d0d1e395380bdc395d0234c69bd3f4ed8e65c4f241ef"),
    ("public static void i();","public static void method3153();",62,0,2,6,
     "8d100c46b7854f579e97a703ce717c4a1ee7d0785d2821aa91bea8f369f75901"),
    ("public static void j();","public static void method236();",19,0,2,2,
     "504e88113d9f8744fe6bc8fc82cda5f5120f963cb14beecc35541cc00d2e25db"),
    ("public static void a(rs.n.c.ap$c);",
     "public static void method2689(rs.interfaces.widgets.Class178);",243,0,26,16,
     "a7de3252557f43b328325dc8d2d925e688d648026c401f8d570712dbde8a5b0e"),
    ("public rs.n.c.ap(rs.l.K[]);",
     "public rs.interfaces.widgets.Class179(rs.graphics.HitsplatFont[]);",4,0,0,1,
     "1c5f629d4f842c62434516fb803e0c31f03caef33589461ec47503e0f7075814"),
    ("public void a();","public void register();",438,0,0,21,
     "c5208f52477762f4cf219eece66a757bd60949cc774510d32d28b5fc372a9e57"),
    ("public static void m(int);","public static void method640(int);",76,0,14,10,
     "f3bc09e42a9a9fe8fe8e3ee5e75a2fd615737478a815ac11206131b4efba0def"),
    ("public static void k();","public static void method1241();",43,3,8,9,
     "0bee5d15e2894694300aea80e2cabeced459fe3be264de5dae863cb4d56af387"),
    ("public void l();","public void method1592();",160,35,0,9,
     "4de2968505153daeb46c44753705462915bd8a0b5c99b6115641e67b51eec835"),
    ("public void m();","public void method2352();",1580,24,18,23,
     "458cdae2b202c9ad8c2d1930f4117f6a8d460058c6ecaac749a3b10eaf857422"),
    ("public void n();","public void method3532();",419,26,13,8,
     "2359b62bd9728cf457d16f1f84700caccce10fe6ddcca64177335e016cd5cf6b"),
    ("public void o();","public void method892();",760,90,0,8,
     "ab863c2ec0611355af31266de4918db70952b04dac8d51da0f920b03137acaeb"),
    ("public void p();","public void method1712();",487,0,0,3,
     "1cf53f91a9e8f611f7db442eb177bdfd90c621ff6ab68ab48dcf4d521810d86b"),
    ("static {};","static {};",13,0,0,5,
     "9f83ac257dada6fd2f01e2d04f0ac71adbb4d90b461d7a3764b085990a34b9c7"),
)


class R220UnifiedSpellbookError(ValueError):
    pass


def need(ok,reason):
    if not ok:
        raise R220UnifiedSpellbookError(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def file_sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as stream:
        for data in iter(lambda:stream.read(1048576),b""):
            h.update(data)
    return h.hexdigest()


def reconstruct_only_pinned_compiler_shape(real_source, *, enforce_sha=True):
    """Reconstruct the ONE readable source by exactly five audited edits."""
    need(isinstance(real_source,(str,bytes)),
         "R220_EXISTING_READABLE_JAVA_SOURCE_REQUIRED")
    if isinstance(real_source,bytes):
        real_source=real_source.decode("utf-8")
    if enforce_sha:
        need(sha(real_source.encode())==EXISTING_READABLE_JAVA_SHA256,
             "R220_ORIGINAL_READABLE_CLASS179_JAVA_SHA_CHANGED")
    filter_method=extract_actual_donor_method(real_source)
    filter_normalized=normalize_existing_method_for_original_javac(
        filter_method,require_pin=enforce_sha)
    ancient=extract_existing_method(real_source,"method3532")
    ancient_normalized=normalize_ancient_compiler_shape(
        ancient,pin=enforce_sha)
    need(real_source.count(filter_method)==1 and
         real_source.count(ancient)==1,
         "R220_METHOD_BODY_REPLACEMENT_NOT_UNIQUE")
    result=real_source.replace(filter_method,filter_normalized,1)
    result=result.replace(ancient,ancient_normalized,1)
    if enforce_sha:
        need(sha(result.encode())==NORMALIZED_WHOLE_JAVA_SHA256,
             "R220_ONLY_FIVE_PINNED_COMPILER_SHAPE_EDITS_ALLOWED")
    return result


def audit_single_class_method_code(original_javap,readable_javap, *,
                                   methods=METHOD_SPECS,
                                   require_full_inventory=True):
    """Compare ALL JVM Code including branch ordinal and symbolic aliases.

    Every bytecode row must match except the exact ldc->ldc_w opcode
    encoding changes that result from the different constant pool.
    No other opcode difference and no non-member operand change is allowed.
    Branches must land on the same INSTRUCTION INDEX in both JVM Methods.
    """
    need(isinstance(methods,(tuple,list)) and len(methods)>0,
         "R220_NONEMPTY_METHOD_SPEC_REQUIRED")
    proofs=[];sum_op=0;sum_widen=0;sum_alias=0
    for old_title,new_title,expected_ops,widenings,branches,alias_count,pin in methods:
        before=parse_javap_code(original_javap,old_title)
        after=parse_javap_code(readable_javap,new_title)
        need(len(before)==len(after)==expected_ops,
             "R220_ORIGINAL_UNIFIED_METHOD_INSTRUCTION_COUNT_CHANGED_"+old_title)
        original_offsets={row[0]:i for i,row in enumerate(before)}
        readable_offsets={row[0]:i for i,row in enumerate(after)}
        aliases={};wide=0;branch=0
        for i,(a,b) in enumerate(zip(before,after)):
            o,op,operand=a
            no,nop,noperand=b
            if op!=nop:
                need(op=="ldc" and nop=="ldc_w",
                     "R220_NONCONSTANTPOOL_JVM_OPCODE_CHANGED")
                wide+=1
            need(no-o==wide-(1 if op=="ldc" and nop=="ldc_w" else 0),
                 "R220_JVM_BYTE_OFFSET_NOT_EXPLAINED_BY_LDC_W")
            if op in BRANCH_OPCODES:
                need(re.fullmatch(r"-?\d+",operand or "") and
                     re.fullmatch(r"-?\d+",noperand or ""),
                     "R220_BRANCH_DESTINATION_NOT_RESOLVED")
                destination=int(operand)
                new_destination=int(noperand)
                need(destination in original_offsets and
                     new_destination in readable_offsets and
                     original_offsets[destination]==readable_offsets[new_destination],
                     "R220_CONTROL_FLOW_TARGET_INSTRUCTION_INDEX_DRIFT")
                branch+=1
            elif operand!=noperand:
                need(operand.startswith(SYMBOL_PREFIXES) and
                     noperand.startswith(SYMBOL_PREFIXES),
                     "R220_NON_SYMBOLIC_JVM_OPERAND_CHANGED")
                if operand in aliases:
                    need(aliases[operand]==noperand,
                         "R220_ORIGINAL_MEMBER_MAP_NOT_SINGLE_VALUED")
                aliases[operand]=noperand
        alias_sha=sha(json.dumps(
            aliases,sort_keys=True,separators=(",",":")).encode())
        need(wide==widenings and branch==branches and
             len(aliases)==alias_count and alias_sha==pin,
             "R220_UNIFIED_JVM_OWNER_ALIAS_OR_ENCODING_MANIFEST_DRIFT_"+old_title)
        need(before[-1][1]=="return" and after[-1][1]=="return",
             "R220_ORIGINAL_AND_REBUILT_METHOD_NO_NORMAL_EXIT")
        proofs.append({
            "original":old_title,
            "readable":new_title,
            "verified_original_jvm_instructions":expected_ops,
            "allowed_ldc_to_ldc_w":wide,
            "control_flow_branches_by_instruction_index":branch,
            "original_to_readable_member_aliases":alias_count,
            "alias_manifest_sha256":alias_sha,
        })
        sum_op+=expected_ops;sum_widen+=wide;sum_alias+=alias_count
    if require_full_inventory:
        need(len(proofs)==14 and sum_op==4314 and
             sum_widen==178 and sum_alias==125,
             "R220_FULL_FOURTEEN_METHOD_JVM_MANIFEST_REQUIRED")
    return {
        "schema_version":1,
        "kind":"v309_one_compiled_Class179_original_method_semantics_r220",
        "verified_method_count":len(proofs),
        "verified_original_jvm_instructions":sum_op,
        "only_ldc_to_ldc_w_opcode_changes":sum_widen,
        "verified_member_aliases_across_methods":sum_alias,
        "full_class_original_jvm_code_equivalent_under_verified_renames":True,
        "original_bytecode_offsets_identical_claimed":False,
        "original_classfile_binary_byte_identity_claimed":False,
        "methods":proofs,
    }


def verify_pinned_single_compiled_class(original_jar,private_source_tree_zip,
                                        normalized_java_source,
                                        compiled_readable_class, *,
                                        original_jar_sha256=CANONICAL_V309,
                                        source_tree_sha256=SOURCE_TREE_SHA256,
                                        original_class_sha256=ORIGINAL_CLASS_SHA256,
                                        require_reference_compiled_class_sha=False):
    need(file_sha(original_jar)==original_jar_sha256 and
         file_sha(private_source_tree_zip)==source_tree_sha256,
         "R220_PRIVATE_V309_ORIGINAL_JAR_OR_SOURCE_ZIP_SHA_REQUIRED")
    with ZipFile(original_jar) as jar:
        need(jar.namelist().count("rs/n/c/ap.class")==1,
             "R220_ORIGINAL_SPELLBOOK_CLASS_ENTRY_NOT_UNIQUE")
        original=jar.read("rs/n/c/ap.class")
    need(sha(original)==original_class_sha256,
         "R220_ORIGINAL_SPELLBOOK_CLASSFILE_SHA_CHANGED")
    with ZipFile(private_source_tree_zip) as tree:
        need(tree.namelist().count(SOURCE_ENTRY)==1,
             "R220_EXISTING_READABLE_JAVA_ENTRY_NOT_UNIQUE")
        donor=tree.read(SOURCE_ENTRY)
    expected_java=reconstruct_only_pinned_compiler_shape(donor)
    need(Path(normalized_java_source).read_bytes()==expected_java.encode(),
         "R220_UNIFIED_JAVA_NOT_EXACTLY_ORIGINAL_PLUS_FIVE_EDITS")
    result_class=Path(compiled_readable_class).read_bytes()
    if require_reference_compiled_class_sha:
        need(sha(result_class)==REFERENCE_SINGLE_COMPILED_CLASS_SHA256,
             "R220_REFERENCE_LOCAL_UNIFIED_CLASS_SHA_CHANGED")
    left=parse_class(original)
    right=parse_class(result_class)
    need(left.name=="rs/n/c/ap" and
         right.name=="rs/interfaces/widgets/Class179" and
         left.super_name=="rs/n/c" and
         right.super_name=="rs/interfaces/widgets/Widget" and
         left.major==right.major==53 and
         left.access==right.access and
         len(left.fields)==len(right.fields)==14 and
         len(left.methods)==len(right.methods)==14,
         "R220_FULL_CLASS_JVM_HEADER_OR_FIELD_METHOD_INVENTORY_MISMATCH")
    javap=shutil.which("javap")
    need(javap is not None,"R220_JDK_JAVAP_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="spk-r220-bytecode-") as tmp:
        root=Path(tmp)
        target=root/"rs/interfaces/widgets/Class179.class"
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(result_class)
        def disasm(cp,owner):
            try:
                return subprocess.run(
                    [javap,"-p","-c","-classpath",str(cp),owner],
                    cwd=root,capture_output=True,text=True,timeout=60,
                    check=True).stdout
            except (OSError,subprocess.TimeoutExpired,
                    subprocess.CalledProcessError) as exc:
                raise R220UnifiedSpellbookError(
                    "R220_JAVAP_FULL_CLASS_INSPECTION_ABORTED") from exc
        original_text=disasm(original_jar,"rs.n.c.ap")
        candidate_text=disasm(root,"rs.interfaces.widgets.Class179")
    result=audit_single_class_method_code(original_text,candidate_text)
    need(file_sha(original_jar)==original_jar_sha256 and
         file_sha(private_source_tree_zip)==source_tree_sha256,
         "R220_PRIVATE_ORIGINAL_EVIDENCE_CHANGED_DURING_REPLAY")
    return {
        **result,
        "original_class_sha256":original_class_sha256,
        "original_decompiled_java_sha256":EXISTING_READABLE_JAVA_SHA256,
        "exact_normalized_whole_java_sha256":NORMALIZED_WHOLE_JAVA_SHA256,
        "actual_rebuilt_readable_class_sha256":sha(result_class),
        "single_full_fourteen_method_source_class_built":True,
        "isolated_dependency_sources_genuine_original_verified":False,
        "original_game_executed":False,
        "entire_original_client_compiled":False,
        "redistribution_authorized":False,
    }

"""R214: recover 243 exact JVM instructions from the EXISTING v309 Class179.java.

The SHA-pinned, real readable method2689(Class178) is compiler-normalized
using precisely three approved edits (early guard, two List variable
declarations), rather than replaced with guessed behavior. Those edits
preserve the predicate and Java Collection semantics while reproducing the
original bytecode instruction forms and offsets. The complete original
rs/n/c/ap.a(ap$c) Code must match, after exactly 16 explicit resolved
original->readable JVM member aliases. No game method is ever executed.

The *other* original parent methods, binary header, superclass, full client
compile and redistribution remain outside R214's acceptance boundary.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from zipfile import ZipFile

from .bytecode_profile import profile_class_field_accesses
from .private_client_namespace_legalizer_r125 import CANONICAL_V309

JAR_SHA256 = CANONICAL_V309
ORIGINAL_CLASS_SHA256 = (
    "b5e8b958c826dfc0a032f5a6d5d301f0c3405f2b68ed083fcf1ff49f1c8cc8e4"
)
SOURCE_TREE_SHA256 = (
    "cabe0212e59bc7130e8d30548aa3bd23604ce2d019ad8ed879107c59001fdf0d"
)
SOURCE_ENTRY = "recovered-source/v309/src/rs/interfaces/widgets/Class179.java"
SOURCE_SHA256 = (
    "8b8ece40b51b646eeb467ba3d258ab7a97bf65fb9543c846eca276497efe07d2"
)
ORIGINAL_METHOD_BODY_SHA256 = (
    "ec60c977992bb0e02ccba1a00e457f74cf30f135bd0eb8e5c2a5e89bf373ce27"
)
COMPILER_NORMALIZED_BODY_SHA256 = (
    "f45d01c283418f7a48d5c923c6aedb230d61dcb88bd7ee16f8235cc70a3d4f15"
)
ORIGINAL_METHOD_TITLE = "public static void a(rs.n.c.ap$c);"
READABLE_METHOD_TITLE = (
    "public static void method2689(rs.interfaces.widgets.Class178);"
)
ORIGINAL_METHOD = ("a", "(Lrs/n/c/ap$c;)V")
READABLE_METHOD = ("method2689", "(Lrs/interfaces/widgets/Class178;)V")
EXPECTED_INSTRUCTIONS = 243
EXPECTED_LAST_OFFSET = 512

# Each mismatch in original-vs-readable javap output was independently
# inventoried and explicitly permitted. Everything else must match.
SYMBOL_ALIASES = {
    "Field d:Z":"Field field3646:Z",
    "Field rs/n/c/ap$c.a:Lrs/n/c/ap$c;":
        "Field rs/interfaces/widgets/Class178.field3639:Lrs/interfaces/widgets/Class178;",
    "Field H:[Lrs/n/e;":
        "Field widgetTable:[Lrs/interfaces/WidgetComponent;",
    "Field rs/n/e.al:[I":
        "Field rs/interfaces/WidgetComponent.children:[I",
    "Field rs/n/c/ap$a.c:Lrs/n/c/ap$a;":
        "Field rs/interfaces/widgets/Class176.field3592:Lrs/interfaces/widgets/Class176;",
    "Method rs/n/c/ap$b.a:(I)Lrs/n/c/ap$b;":
        "Method rs/interfaces/widgets/Class177.method1431:(I)Lrs/interfaces/widgets/Class177;",
    "Field rs/n/c/ap$b.R:Lrs/n/c/ap$a;":
        "Field rs/interfaces/widgets/Class177.field3637:Lrs/interfaces/widgets/Class176;",
    "Field rs/n/c/ap$b.Q:I":
        "Field rs/interfaces/widgets/Class177.field3636:I",
    "Field e:Z":"Field field3647:Z",
    "Method rs/gui/Launcher.n:()Lrs/gui/Launcher;":
        "Method rs/gui/Launcher.getInstance:()Lrs/gui/Launcher;",
    "Method rs/gui/Launcher.o:()Lrs/Client;":
        "Method rs/gui/Launcher.getClient:()Lrs/Client;",
    "Field rs/Client.eo:[I":"Field rs/Client.skillLevels:[I",
    "Field f:Ljava/util/List;":"Field field3648:Ljava/util/List;",
    "class rs/n/c/ap$a":"class rs/interfaces/widgets/Class176",
    "Field rs/n/e.am:[I":
        "Field rs/interfaces/WidgetComponent.childX:[I",
    "Field rs/n/e.bc:[I":
        "Field rs/interfaces/WidgetComponent.childY:[I",
}

# Explicitly compiler-only signatures — not original or deobfuscated source
# implementations. None enters the canonical full private source tree.
SUPPORT_DECLARATIONS = {
    "rs/interfaces/WidgetComponent.java": (
        "package rs.interfaces; public class WidgetComponent {"
        "public static WidgetComponent[] widgetTable;"
        "public int[] children,childX,childY;}"
    ),
    "rs/interfaces/widgets/Class178.java": (
        "package rs.interfaces.widgets; public enum Class178 {SPELLS;"
        "public static final Class178 field3639=SPELLS;}"
    ),
    "rs/interfaces/widgets/Class176.java": (
        "package rs.interfaces.widgets; public enum Class176 {COMBAT,UTILITY;"
        "public static final Class176 field3592=UTILITY;}"
    ),
    "rs/interfaces/widgets/Class177.java": (
        "package rs.interfaces.widgets; public class Class177 {"
        "public int field3636; public Class176 field3637;"
        "public static Class177 method1431(int i){return null;}}"
    ),
    "rs/gui/Launcher.java": (
        "package rs.gui; import rs.Client; public class Launcher {"
        "public static Launcher getInstance(){return null;}"
        "public Client getClient(){return null;}}"
    ),
    "rs/Client.java": (
        "package rs; public class Client {public int[] skillLevels;}"
    ),
}


class R214OriginalReadableFilterError(ValueError):
    pass


def need(ok, message):
    if not ok:
        raise R214OriginalReadableFilterError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    hasher=hashlib.sha256()
    with Path(path).open("rb") as stream:
        for part in iter(lambda:stream.read(1024*1024),b""):
            hasher.update(part)
    return hasher.hexdigest()


def extract_actual_donor_method(source, method="method2689",
                                parameter_type="Class178"):
    matches=list(re.finditer(
        r"(?m)^\s*public\s+static\s+void\s+"+re.escape(method)+
        r"\s*\("+re.escape(parameter_type)+r"\s+var0\)\s*\{",source))
    if len(matches)==0 and parameter_type=="Class178":
        # Invented CI fixtures use Category rather than the private
        # original Class178 type. Exact private replay is separately SHA-pinned.
        matches=list(re.finditer(
            r"(?m)^\\s*public\\s+static\\s+void\\s+"+re.escape(method)+
            r"\\s*\\(Category\\s+var0\\)\\s*\\{",source))
    need(len(matches)==1,"R214_VERBATIM_DONOR_METHOD_NOT_UNIQUE")
    start=matches[0].start()
    i=source.index("{",start)+1
    depth=1
    while depth and i<len(source):
        if source[i]=="{":depth+=1
        elif source[i]=="}":depth-=1
        i+=1
    need(depth==0 and i-start<7000,
         "R214_UNBALANCED_OR_OVERSIZED_SOURCE_METHOD")
    return source[start:i]


def normalize_existing_method_for_original_javac(method, *,
                                                  require_pin=True):
    """Only 3 small, behavior-preserving compiler-shape changes.

    (1) Original Code has an early return when the filter is disabled.
    (2-3) Original's ArrayList variables have List compile-time type:
           invokeinterface rather than invokevirtual at seven sites.
    """
    need(type(method) is str,"R214_SOURCE_METHOD_TEXT_REQUIRED")
    if require_pin:
        need(sha(method.encode("utf-8"))==ORIGINAL_METHOD_BODY_SHA256,
             "R214_ORIGINAL_UNCHANGED_DONOR_METHOD_SHA256_MISMATCH")
    need(method.count("if (field3646) {")==1
         and method.count("ArrayList var2 = new ArrayList();")==1
         and method.count("ArrayList var3 = new ArrayList();")==1
         and method.endswith("         }\n      }\n   }"),
         "R214_NOT_THE_EXACT_ORIGINAL_JAVA_COMPILER_SHAPE")
    result=method.replace("if (field3646) {",
                          "if (!field3646) return;",1)
    result=result[:-len("      }\n   }")]+"   }"
    result=result.replace("ArrayList var2 = new ArrayList();",
                          "List var2 = new ArrayList();",1)
    result=result.replace("ArrayList var3 = new ArrayList();",
                          "List var3 = new ArrayList();",1)
    need(result.count("if (!field3646) return;")==1
         and result.count("List var2 = new ArrayList();")==1
         and result.count("List var3 = new ArrayList();")==1,
         "R214_UNEXPECTED_NORMALIZATION_REPLACEMENT")
    if require_pin:
        need(sha(result.encode("utf-8"))==COMPILER_NORMALIZED_BODY_SHA256,
             "R214_NORMALIZED_DONOR_METHOD_SHA256_MISMATCH")
    return result


def parse_javap_code(output,title):
    """Parse the complete selected method's decoded javap -p -c Code."""
    lines=output.splitlines()
    headers=[i for i,line in enumerate(lines) if line.strip()==title]
    need(len(headers)==1,"R214_JVM_METHOD_HEADER_NOT_UNIQUE")
    start=headers[0]+1
    need(start<len(lines) and lines[start].strip()=="Code:",
         "R214_JVM_CODE_ATTRIBUTE_MISSING")
    result=[]
    for line in lines[start+1:]:
        match=re.match(r"^\s*(\d+):\s+(\w+)(?:\s+(.*))?$",line)
        if not match:
            break
        tail=(match.group(3) or "").strip()
        if "//" in tail:
            tail=tail.split("//",1)[1].strip()
        elif tail.startswith("#"):
            raise R214OriginalReadableFilterError(
                "R214_UNRESOLVED_JVM_CONSTANT_POOL_SYMBOL")
        result.append((int(match.group(1)),match.group(2),tail))
    need(result and len({i[0] for i in result})==len(result),
         "R214_JVM_METHOD_INSTRUCTION_DECODE_EMPTY_OR_DUPLICATE")
    return result


def compare_full_original_readable_code(original_javap,readable_javap, *,
                                        original_title=ORIGINAL_METHOD_TITLE,
                                        readable_title=READABLE_METHOD_TITLE,
                                        aliases=SYMBOL_ALIASES,
                                        expected_instructions=EXPECTED_INSTRUCTIONS,
                                        expected_last_offset=EXPECTED_LAST_OFFSET):
    """An exact 243-row comparison: offset, opcode, branch and member symbol."""
    before=parse_javap_code(original_javap,original_title)
    after=parse_javap_code(readable_javap,readable_title)
    need(len(before)==len(after)==expected_instructions
         and before[-1]==(expected_last_offset,"return","")
         and after[-1]==(expected_last_offset,"return",""),
         "R214_ORIGINAL_LONG_METHOD_LENGTH_OR_END_DRIFT")
    converted=[
        (offset,opcode,aliases.get(operand,operand))
        for offset,opcode,operand in before
    ]
    need(converted==after,"R214_ORIGINAL_243_JVM_CODE_OR_SYMBOL_DRIFT")
    # Confirm alias mapping is not an inert whitelist: the original JVM
    # method must exercise each explicitly accepted rename.
    used={operand for _,_,operand in before if operand in aliases}
    need(used==set(aliases),"R214_UNUSED_OR_INCOMPLETE_SYMBOLIC_ALIAS_TABLE")
    return {
        "original_decoded_jvm_instructions":len(before),
        "readable_recompiled_jvm_instructions":len(after),
        "matched_original_byte_offsets_opcodes_and_operands":True,
        "all_branch_target_addresses_equal":True,
        "actual_distinct_renamed_member_or_type_symbols":len(used),
    }


def verify_pinned_v309_readable_long_filter_method(
        original_jar,private_source_tree, *,
        original_jar_sha256=JAR_SHA256,
        original_class_sha256=ORIGINAL_CLASS_SHA256,
        source_tree_sha256=SOURCE_TREE_SHA256,
        donor_java_sha256=SOURCE_SHA256):
    need(file_sha(original_jar)==original_jar_sha256
         and file_sha(private_source_tree)==source_tree_sha256,
         "R214_PRIVATE_JAR_OR_DECOMPILED_SOURCE_SHA_MISMATCH")
    with ZipFile(original_jar) as jar:
        name="rs/n/c/ap.class"
        need(jar.namelist().count(name)==1,
             "R214_ORIGINAL_PARENT_JVM_CLASS_NOT_UNIQUE")
        original=jar.read(name)
    need(sha(original)==original_class_sha256,
         "R214_ORIGINAL_PARENT_CLASS_SHA_CHANGED")
    with ZipFile(private_source_tree) as tree:
        need(tree.namelist().count(SOURCE_ENTRY)==1,
             "R214_READABLE_DONOR_JAVA_SOURCE_NOT_UNIQUE")
        donor=tree.read(SOURCE_ENTRY)
    need(sha(donor)==donor_java_sha256,
         "R214_READABLE_DONOR_JAVA_SHA_CHANGED")
    verbatim=extract_actual_donor_method(donor.decode("utf-8"))
    normalized=normalize_existing_method_for_original_javac(verbatim)
    source=(
        "package rs.interfaces.widgets;\n"
        "import java.util.*;\n"
        "import rs.gui.Launcher;\n"
        "import rs.interfaces.WidgetComponent;\n"
        "public class Class179 extends WidgetComponent {\n"
        " public static boolean field3646,field3647;\n"
        " public static List<Class176> field3648;\n"
        +normalized+"\n}\n"
    )
    java=shutil.which("javac")
    javap=shutil.which("javap")
    need(java is not None and javap is not None,
         "R214_JAVA9_COMPILER_AND_JAVAP_REQUIRED")
    with tempfile.TemporaryDirectory(prefix="spk-r214-filter-") as tmp:
        root=Path(tmp)
        inputs={
            "rs/interfaces/widgets/Class179.java":source,
            **SUPPORT_DECLARATIONS,
        }
        paths=[]
        for relative,body in inputs.items():
            target=root/"src"/relative
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_text(body,encoding="utf-8")
            paths.append(str(target))
        empty=root/"empty";out=root/"classes"
        empty.mkdir();out.mkdir()
        env=os.environ.copy()
        for key in ("CLASSPATH","JAVA_TOOL_OPTIONS",
                    "JDK_JAVA_OPTIONS","_JAVA_OPTIONS"):
            env.pop(key,None)
        try:
            built=subprocess.run(
                [java,"--release","9","-g:none","-proc:none",
                 "-implicit:none","-classpath",str(empty),
                 "-sourcepath",str(empty),"-d",str(out),*paths],
                cwd=root,env=env,stdin=subprocess.DEVNULL,
                capture_output=True,timeout=100,check=False)
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise R214OriginalReadableFilterError(
                "R214_ISOLATED_COMPILER_ABORTED") from exc
        emitted={p.relative_to(out).as_posix()
                 for p in out.rglob("*.class")}
        need(built.returncode==0
             and emitted=={path[:-5]+".class" for path in inputs},
             "R214_SOURCE_BUILD_FAILURE_OR_EXTRA_EMITTED_JVM_CLASSES")
        candidate=(out/"rs/interfaces/widgets/Class179.class").read_bytes()
        def disassemble(path,owner):
            try:
                return subprocess.run(
                    [javap,"-p","-c","-classpath",str(path),owner],
                    capture_output=True,text=True,timeout=40,check=True,
                    cwd=root,env=env).stdout
            except (OSError,subprocess.CalledProcessError,
                    subprocess.TimeoutExpired) as exc:
                raise R214OriginalReadableFilterError(
                    "R214_JAVAP_DISASSEMBLY_ABORTED") from exc
        left=disassemble(original_jar,"rs.n.c.ap")
        right=disassemble(out,"rs.interfaces.widgets.Class179")
    # Independently check decoded method Code/header limits using the
    # repository parser in addition to the full javap instruction audit.
    old=profile_class_field_accesses(original)
    new=profile_class_field_accesses(candidate)
    def exactly_one(profile,name,descriptor):
        found=[m for m in profile["methods"]
               if (m["name"],m["descriptor"])==(name,descriptor)]
        need(len(found)==1 and found[0]["code_length"] is not None,
             "R214_EXACT_ORIGINAL_JVM_METHOD_DESCRIPTOR_REQUIRED")
        return found[0]
    om=exactly_one(old,*ORIGINAL_METHOD)
    nm=exactly_one(new,*READABLE_METHOD)
    need(om["access"]==nm["access"]==0x0009
         and om["code_length"]==nm["code_length"]==513
         and om["max_stack"]==nm["max_stack"]
         and om["max_locals"]==nm["max_locals"]
         and om["exception_handlers"]==nm["exception_handlers"]
         and om["stackmap_table_present"]==nm["stackmap_table_present"],
         "R214_ORIGINAL_JVM_CODE_LIMITS_EXCEPTION_HANDLER_DRIFT")
    result=compare_full_original_readable_code(left,right)
    need(file_sha(original_jar)==original_jar_sha256
         and file_sha(private_source_tree)==source_tree_sha256,
         "R214_PRIVATE_BINARY_OR_SOURCE_CHANGED_DURING_REPLAY")
    return {
        "schema_version":1,
        "kind":"v309_existing_class179_long_filter_243_original_jvm_code_r214",
        **result,
        "original_method":ORIGINAL_METHOD,
        "readable_method":READABLE_METHOD,
        "original_class_sha256":original_class_sha256,
        "existing_readable_source_sha256":donor_java_sha256,
        "original_unchanged_donor_method_sha256":ORIGINAL_METHOD_BODY_SHA256,
        "minimal_compiler_normalized_method_sha256":
            COMPILER_NORMALIZED_BODY_SHA256,
        "source_normalizations":[
            "nested boolean guard -> equivalent early return",
            "two ArrayList variable declarations -> List static type",
        ],
        "real_existing_source_used":True,
        "compiler_only_dependency_declarations_used":len(
            SUPPORT_DECLARATIONS),
        "compiler_helpers_accepted_as_original_source":False,
        "parent_full_14_method_class_reconstructed":False,
        "original_game_code_executed":False,
        "complete_client_compiles":False,
        "derived_source_redistribution_authorized":False,
    }

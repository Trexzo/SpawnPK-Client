"""R84: exact original 364-op v309 settings-save file I/O envelope.

Reconstruct only original bounded File/BufferedWriter creation, final close,
Paths.get, Files.copy/delete, and catch printStackTrace Java source fragments.
Never claim a complete compiled save method from this bounded evidence.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
from zipfile import ZipFile

from .bytecode_profile import profile_jar_class
from .mutable_scalar_initializer_source import _digest, _instructions
from .properties_save_writer_source import SaveWriterSourceError
from .properties_save_special_source import (
    plan_original_special_save_sources, source_field, recipe,
)

PIN=re.compile(r"[a-fA-F0-9]{64}\Z")
OPEN=("0xbb","0x59","0xb2","0xba","0xb7","0x4b",
      "0x2a","0xb6","0x9a","0x2a","0xb6","0x57",
      "0xbb","0x59","0xbb","0x59","0x2a","0xb7","0xb7","0x4c")
TAIL=("0x2b","0xb6","0xb2","0xba","0x03","0xbd","0xb8","0x4d",
      "0x2c","0xb2","0x03","0xbd","0xb8","0x04","0xbd","0x59",
      "0x03","0xb2","0x53","0xb8","0x57","0x2c","0xb8",
      "0xa7","0x4b","0x2a","0xb6","0xb1")


def need(ok, why):
    if not ok:
        raise SaveWriterSourceError(why)


def call(row,opcode,owner,name,descriptor):
    return (row.get("opcode")==opcode and row.get("owner")==owner
            and row.get("name")==name and row.get("descriptor")==descriptor)


def _join(literals,expressions):
    need(len(literals)==len(expressions)+1,
         "STRING_CONCAT_RECIPE_DYNAMIC_ARGUMENT_COUNT_MISMATCH")
    pieces=[]
    for index,expression in enumerate(expressions):
        if literals[index]:
            pieces.append(json.dumps(literals[index],ensure_ascii=True))
        pieces.append(expression)
    if literals[-1]:
        pieces.append(json.dumps(literals[-1],ensure_ascii=True))
    return " + ".join(pieces)


def plan_original_save_io_envelope(profile,private_method,descriptor):
    candidates=[m for m in profile.get("methods",[])
                if m.get("name")==private_method and m.get("descriptor")==descriptor]
    need(len(candidates)==1 and descriptor=="()V",
         "ORIGINAL_SAVE_METHOD_NOT_UNIQUE")
    method=candidates[0]
    rows=_instructions(method)
    need(method.get("access")==0x000a and len(rows)==364
         and tuple(x.get("opcode") for x in rows[:20])==OPEN
         and tuple(x.get("opcode") for x in rows[-28:])==TAIL,
         "ORIGINAL_FILE_IO_JVM_OPCODE_ENVELOPE_DRIFT")
    need(rows[0]["offset"]==0 and rows[19]["offset"]==43
         and rows[20]["offset"]==44
         and rows[-28]["offset"]==871
         and rows[-1]["offset"]==928
         and rows[-1]["length"]==1,
         "ORIGINAL_SAVE_FILE_IO_OFFSET_BOUNDARIES_DRIFT")
    handlers=method.get("exception_handlers")
    need(isinstance(handlers,list) and len(handlers)==1
         and all(handlers[0].get(k)==v for k,v in (
             ("start_pc",0),("end_pc",920),("handler_pc",923),
             ("catch_type","java/lang/Exception"))),
         "ORIGINAL_SAVE_EXACT_OUTER_EXCEPTION_TABLE_DRIFT")
    need(rows[8].get("branch_target_offset")==28
         and rows[-5].get("branch_target_offset")==928,
         "ORIGINAL_SAVE_FILE_GUARD_OR_CATCH_BRANCH_DRIFT")
    need(rows[0].get("type")=="java/io/File"
         and rows[12].get("type")=="java/io/BufferedWriter"
         and rows[14].get("type")=="java/io/FileWriter"
         and call(rows[4],"0xb7","java/io/File","<init>","(Ljava/lang/String;)V")
         and call(rows[7],"0xb6","java/io/File","exists","()Z")
         and call(rows[10],"0xb6","java/io/File","createNewFile","()Z")
         and call(rows[17],"0xb7","java/io/FileWriter","<init>","(Ljava/io/File;)V")
         and call(rows[18],"0xb7","java/io/BufferedWriter","<init>","(Ljava/io/Writer;)V"),
         "ORIGINAL_FILE_CREATION_AND_WRITER_CTOR_MISMATCH")
    t=rows[-28:]
    need(call(t[1],"0xb6","java/io/BufferedWriter","close","()V")
         and t[5].get("type")=="java/lang/String"
         and t[11].get("type")=="java/lang/String"
         and t[14].get("type")=="java/nio/file/CopyOption",
         "ORIGINAL_WRITER_CLOSE_AND_FILE_ARRAY_TYPES_DIFFER")
    for index in (6,12):
        need(call(t[index],"0xb8","java/nio/file/Paths","get",
                  "(Ljava/lang/String;[Ljava/lang/String;)Ljava/nio/file/Path;"),
             "ORIGINAL_PATHS_GET_DESCRIPTOR_DRIFT")
    need(call(t[19],"0xb8","java/nio/file/Files","copy",
              "(Ljava/nio/file/Path;Ljava/nio/file/Path;[Ljava/nio/file/CopyOption;)Ljava/nio/file/Path;")
         and call(t[22],"0xb8","java/nio/file/Files","delete",
                  "(Ljava/nio/file/Path;)V")
         and call(t[26],"0xb6","java/lang/Exception","printStackTrace","()V")
         and (t[17].get("owner"),t[17].get("name"),t[17].get("descriptor"))
             ==("java/nio/file/StandardCopyOption","REPLACE_EXISTING",
                "Ljava/nio/file/StandardCopyOption;"),
         "ORIGINAL_FILES_COPY_DELETE_OPTION_OR_EXCEPTION_SIDE_EFFECT_DRIFT")
    for index in (9,19,24):
        if index==19:continue
    # Three reads must use the same original static String field.
    original_field=rows[2]
    need(all(all(rows[index].get(k)==original_field.get(k)
                 for k in ("opcode","owner","name","descriptor"))
             for index in (338,345)),
         "ORIGINAL_FILE_PATH_FIELD_REFERENCE_CHANGED")
    field=source_field(profile,original_field,"Ljava/lang/String;")
    start_recipe=recipe(profile,rows[3],"Ljava/lang/String;",1)
    end_recipe=recipe(profile,t[3],"Ljava/lang/String;",1)
    # Exact R82 + R83 source classification is independently required.
    sites=plan_original_special_save_sources(profile,private_method,descriptor)
    need(sites["original_BW_write_sites_classified"]==47,
         "ALL_ORIGINAL_WRITES_NOT_CLASSIFIED")
    prefix=("java.io.File originalLocalSlot0 = new java.io.File("
            +_join(start_recipe,[field])+");\n"
            "if (!originalLocalSlot0.exists()) {\n"
            "    originalLocalSlot0.createNewFile();\n"
            "}\n"
            "java.io.BufferedWriter originalLocalSlot1 = "
            "new java.io.BufferedWriter(new java.io.FileWriter(originalLocalSlot0));\n")
    tail=("originalLocalSlot1.close();\n"
          "java.nio.file.Path originalLocalSlot2 = java.nio.file.Paths.get("
          +_join(end_recipe,[field])+");\n"
          "java.nio.file.Files.copy(originalLocalSlot2, "
          "java.nio.file.Paths.get("+field+"), "
          "java.nio.file.StandardCopyOption.REPLACE_EXISTING);\n"
          "java.nio.file.Files.delete(originalLocalSlot2);\n")
    handler="catch (java.lang.Exception originalSaveException) {\n    originalSaveException.printStackTrace();\n}\n"
    return {
        "private_source_open_prefix":prefix,
        "private_source_close_copy_delete_tail":tail,
        "private_source_original_exception_catch":handler,
        "original_file_io_open_prefix_instructions":20,
        "original_file_io_close_copy_delete_catch_instructions":28,
        "original_BW_write_sites_preverified":47,
        "original_outer_Exception_handler_exact":True,
        "original_Files_copy_delete_operand_descriptors_exact":True,
        "complete_original_364_instruction_method_compiled":False,
        "all_writer_site_source_fragments_combined_and_compiled":False,
        "full_runtime_and_filesystem_side_effects_equivalent":False,
    }


def replay_private_save_io(jar,entry,method,descriptor,out,*,original_sha256):
    jar,out=Path(jar),Path(out)
    need(not out.exists() and not out.is_symlink(),"OUTPUT_ALREADY_EXISTS")
    need(isinstance(original_sha256,str) and PIN.fullmatch(original_sha256)
         and jar.is_file() and not jar.is_symlink()
         and _digest(jar)==original_sha256.lower(),
         "ORIGINAL_COMPLETE_JAR_SHA256_MISMATCH")
    need(isinstance(entry,str) and entry.endswith(".class")
         and not entry.startswith("/") and "\\" not in entry
         and all(p not in ("",".","..") and ":" not in p
                 for p in entry.split("/")),"INVALID_PRIVATE_CLASS_PATH")
    with ZipFile(jar) as z:
        need(z.namelist().count(entry)==1,"ORIGINAL_OWNER_CLASS_NOT_UNIQUE")
    profile=profile_jar_class(jar,entry)
    p=plan_original_save_io_envelope(profile,method,descriptor)
    need(_digest(jar)==original_sha256.lower(),
         "ORIGINAL_JAR_CHANGED_DURING_REPLAY")
    private={key:p.pop(key) for key in (
        "private_source_open_prefix",
        "private_source_close_copy_delete_tail",
        "private_source_original_exception_catch")}
    encoded=json.dumps(private,sort_keys=True,indent=2)+"\n"
    aggregate={
        "schema_version":1,"kind":"original_v309_private_364_op_save_io_envelope",
        "original_complete_jar_sha256":original_sha256.lower(),
        "private_source_sha256":hashlib.sha256(encoded.encode()).hexdigest(),
        "research_only":True,**p,
    }
    out.mkdir(parents=True,exist_ok=False)
    with (out/"save-io-envelope.private.json").open("x",encoding="utf-8") as f:
        f.write(encoded)
    with (out/"save-io-envelope.aggregate.json").open("x",encoding="utf-8") as f:
        json.dump(aggregate,f,indent=2,sort_keys=True);f.write("\n")
    return aggregate


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ("original_jar","original_class_entry","original_method",
                 "descriptor","new_private_output"):ap.add_argument(name)
    ap.add_argument("--original-sha256",required=True)
    a=ap.parse_args(argv)
    try:
        print(json.dumps(replay_private_save_io(
            a.original_jar,a.original_class_entry,a.original_method,
            a.descriptor,a.new_private_output,
            original_sha256=a.original_sha256),sort_keys=True))
    except (SaveWriterSourceError,OSError,ValueError) as exc:
        ap.error(str(exc))
    return 0
if __name__=="__main__":
    raise SystemExit(main())

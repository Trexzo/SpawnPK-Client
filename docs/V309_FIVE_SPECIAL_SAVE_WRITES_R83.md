# R83: five exceptional original-v309 settings-save writes

After R82's 42 bounded writer source forms, R83 verifies the five original nontrivial write(String) sites in the same 364-instruction settings-save method. Its original-byte-offset windows are exact and version-specific: the indexed int-array loop, three guarded external List.contains(enum) flag writes, and one null-guarded pair of enum.name() fields.

The tool checks all five complete original opcode windows, exact bounds and critical branch targets, original typed static-field references, writer calls and Java 9 StringConcatFactory recipes. It requires R82's 42 source forms to be recognized first. Private Java fragments are saved locally; aggregate results contain counts and digests, not the original obfuscated identifiers or configuration literals.

Private replay:
python -m spk_recovery.properties_save_special_source ORIGINAL_JAR ORIGINAL_OWNER.class ORIGINAL_METHOD "()V" NEW_PRIVATE_OUTPUT --original-sha256 ORIGINAL_WHOLE_JAR_SHA256

The original-JAR bytecode windows and writer-site counts were independently inspected. The generic R83 CLI has not yet passed original-JAR replay. Neither the surrounding file streams and Files.copy/delete behavior nor a complete recompiled 364-instruction method are claimed. All original helper side-effect and runtime parity flags remain false.
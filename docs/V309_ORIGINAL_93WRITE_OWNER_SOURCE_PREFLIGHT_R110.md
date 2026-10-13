# R110 — original-v309 93-write Java9 initializer source preflight (pre-R105)

## Independent actual-original Java9 source reconstruction

Using the pinned complete original v309 client JAR (SHA256 `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`), all 85 original **mutable** owner field writes were reconstructed from their original `<clinit>` bytecode, in addition to the eight already recovered nonconstant-final assignments (R109). Reassembled as original source under the original 126 Java field declarations and four source-legal recovered enums, and compiled using **`javac --release 9 -g:none -proc:none`**, with one explicitly **NONORIGINAL external helper implementation stub** solely for compilation.

The resulting PRIVATE Java9 owner has the same **126 original field declaration identities/access flags/descriptors/33 ConstantValue entries**, after only the source-invalid temporary fourth enum descriptor normalization. Its `<clinit>` contains **213 JVM instructions**, **93/93 matching original ordered own-class `putstatic` field targets** (85 mutable, 8 nonconstant-final), **exactly matching eight branch destination instruction ordinals**, and **matching max_stack=2, max_locals=0**. Opcode comparison: **211/213 direct matches**; the remaining two are Java compiler `ldc`→`ldc_w` constant-pool-width changes, both retaining exact original literal types and values.

The three original StringConcatFactory invokedynamic sites retain their original symbolic bootstrap method and literal recipe values, including two shared conditional sites and one distinct helper-concat recipe. Pre-R105, **two ordinary method-reference names are not equal**: the source compiler synthesized different names for the fourth enum's two exact original private-field synthetic accessors. **Do not call R58 or R107 passed without strict R105 post-javac rebinding and a complete exact-original final replay**. None of the original outer owner's ten methods is yet compiled into this provisional source.

Private source SHA256: `5ddf5896f022b522d08c485f480ce929ade38b3b49d0e5f029d570f6c11e567b`. Private compiled owner-with-93-writes Java9 JAR SHA256: `856ac0bfb0b088c898866f40994dc6ace478d8448959ae9efa2469392839e94f`. No original binary Code bytes transferred. Private bundle is a recovery capsule, not a runnable SpawnPK client.

## R110 public-safe verifier

`spk_recovery.private_original_93write_initializer_source_preflight_r110` reads only explicitly chosen, independently SHA256-pinned original and compiler-built candidate JARs, with the actual original owner class and source-legal fourth-enum simple name supplied via CLI. It verifies all 126 declaration rows (normalized only for one type-identity collision), 33 exact `ConstantValue` fields, all 93 ordered original owner field assignments, exactly 213 instruction opcode roles, exactly two permissible `ldc`→`ldc_w` literal-preserving transformations, eight branch-target instruction ordinals, three **full original symbolic StringConcatFactory bootstrap recipes**, and original JVM stack/local limits. Outputs only a fresh, sanitized aggregate of SHA256 pins and counts. Any other field, opcode, constant value, branch, bootstrap, order or SHA change fails closed.

The verifier intentionally does **not** normalize unmatched original/candidate non-putstatic field or synthetic accessor operand names. They must be checked in the existing R105/R58/R94/R95/R107 exact-original final replay. Strict private source/JAR symbols and source literals are never printed or committed.

Hosted synthetic deterministic profile tests enforce positive all-count comparison and negative cases for altered constants, source-only class descriptor drift, missing/duplicate writes, opcode drift, branch targets, bootstrap drift and stack shape. The real private original-v309 R110 verifier run and composite acceptance still require a private checkout with both original and candidate JAR files. Hosted tests alone are not full client proof.

## Next gates

R109 eight-final source dependency patterns → **R110 original 93-write initializer Java-source preflight** → R106 one StackMap frame normalization → R105 exact original synthetic accessor names → R104 fourth-class binary identity and owner InnerClasses → R95 four nested enum methods → R94 nine owner methods → R58 final initializer → R88 126-field/four-enum exact metadata → R107 complete same postimage acceptance. The original **ten owner method bodies**, external helpers/callback/file I/O and gameplay runtime equivalence remain outstanding.

CLI:

`python -m spk_recovery.private_original_93write_initializer_source_preflight_r110 ORIGINAL_V309.jar SOURCE_COMPILED_CANDIDATE.jar OWNER.class Surrogate FRESH_PRIVATE_REPORT_DIR --original-sha256 ORIGINAL_SHA --candidate-sha256 CANDIDATE_SHA`

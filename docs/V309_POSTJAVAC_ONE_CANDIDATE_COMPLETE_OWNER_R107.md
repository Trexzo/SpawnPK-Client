# R107 — one exact original-v309 post-javac candidate for all owner and nested gates

## Purpose

R97's legacy orchestration treats the **source-compiled** owner as the final accepted candidate. Original v309 contains one fourth enum with a JVM nested simple name **equal to the enclosing owner simple name**, which Java source cannot declare. R90's source-compiler frontier can therefore truthfully report **one missing original nested class** even though four Java9 source enums are present. Requiring zero names *before* JVM rebind blocks the only viable compiler-derived recovery path; relaxing the original R95 or R94 acceptance criteria is **not** permitted.

R107 is an additive, distinct private acceptance tool. It distinguishes the **source preimage** from the **one final accepted postimage**, verifies that the source differs by **exactly the known one nested name** (four original vs four source enum classfiles, no other missing or extra nested classes), and makes all final acceptance depend on a single SHA-pinned **post-javac** JAR.

## Ordered fail-closed gates

1. **R90 source compilation:** SHA-pin the original complete JAR, validate R87 both original 697/364-op methods, R58 original ordered 93 initializer writes, R88 all 126 original owner fields, no missing original owner methods. Require **exactly one unresolved nested binary identity**; independently inspect both ZIP inventories to prove it is only the known source-invalid fourth enum name collision. The provisional source candidate is *never* a final accepted output.
2. **R106 → R105 → R104 → R95:** repair the uniquely proven original case-insensitive enum's `full_frame` metadata without copying Code; bind both fourth enum synthetic accessor declarations and enclosing JVM callsites by exact private field target, restore the fourth JVM binary class identity and all six owner `InnerClasses` rows, then require R95 on all four enum methods and metadata. Require that the final postimage is freshly SHA-pinned and different from source preimage.
3. **R94 on final postimage:** verify all nine original owner non-`<clinit>` method bodies and **1,135 symbolic JVM operands**, under unchanged strict R66/R81 method identity rules. This recheck is intentionally **after** post-javac constant-pool and member reference changes.
4. **R58 and R88 on final postimage:** independently reopen both SHA-pinned JARs, recompare **213 original initializer instructions / 93 ordered writes** and all 126 owner fields, ten method declarations, four exact original nested binary class identities and five class header parity flags. **Zero** extra/missing/drifting original fields, methods, nested classes, or declaration signatures can remain.
5. **Atomic private promotion:** only when all checks pass, promote the single final accepted candidate JAR and a sanitized count/boolean/hash aggregate. Every failure leaves no output. No original binary, Code or proprietary identifiers are published.

## Tests and boundaries

R107 unit tests use deterministic synthetic ZIP original and source candidate fixtures to exercise the exact one-collision inventory; mock only already separately verified R90/R106/R94/R58/R88 semantic gates, and assert that every gate receives the correct SHA-pinned source/final candidate in order. Positive test requires **one final JAR** and no surviving scratch directories. Negative tests veto wrong original SHA, missing unrelated enum, extra original missing method, extra missing enum name, failed R95, postimage hash drift, failed final R94, initializer mismatch and incomplete final owner frontier. R106's standalone hosted tests separately exercise real Java9 compiling, metadata repair and isolated JVM behavior.

**Outstanding:** the complete *real original-v309* R107 CLI invocation with an independently recovered **all-126-field/ten-method owner source tree** and its private alias JSON inputs has not passed. Its absence must never be conflated with hosted synthetic CI success. No external helper implementation, callbacks, filesystem/config side effects, authorial source identity or whole gameplay/runtime equivalence are certified.

## Private CLI

`python -m spk_recovery.private_complete_postjavac_v309_owner_r107 ORIGINAL_V309.jar OWNER.class ORIGINAL_LOADER ORIGINAL_SAVER SOURCE_ROOT OWNER.class CANDIDATE_LOADER CANDIDATE_SAVER LOAD_ALIASES.json SAVE_ALIASES.json CLINIT_ALIASES.json Surrogate FRESH_PRIVATE_OUTPUT --original-sha256 ORIGINAL_SHA --javac JAVAC9_OR_LATER`

Artifacts with original proprietary symbol strings must stay local/private. No original JAR, candidate JAR, recovered Java source or original field/literal/member mappings are committed.

# R105 — exact original v309 synthetic accessor member names and linked outer callsites

## Original-v309 private source evidence

Independent read-only pinned original `client(7).jar` inspection has now recovered a four-enum Java9 source candidate: **4/4 enum classes, 25/25 method opcode sequences, and 295/295 symbolic JVM instruction operands**, after explicitly bounded generated enum constant/values helper aliases. The fourth enum retains two private original String fields; the original has two `ACC_STATIC | ACC_SYNTHETIC` accessors named differently from javac-generated names. A private local prototype mapped those exact field targets, renamed two candidate method declarations, rewired two enclosing-class Methodref references, fixed constant pool construction ordering, and successfully executed the resulting isolated Java9 candidate, including its two getter callbacks, case-insensitive enum lookup and integer-valued enum.

## What R105 adds

`spk_recovery.private_original_synthetic_accessor_rebind_r105` takes separate full original and independently compiled four-enum candidate JARs with exact SHA-256 pins. It identifies each synthetic accessor through the already-reviewed R99 exact private String getfield target, not guessed method names. It patches precisely the two candidate fourth-enum `method_info.name_index` declarations and every `CONSTANT_Methodref` NameAndType entry targeting those methods (including outer Java9-generated caller references). It appends new UTF8/NameAndType constant-pool entries as needed, preserving shared existing constant-pool entries and **all original candidate Code bytes**. Explicitly validates two unique source and target names and requires the enclosing callsites to be updated.

After private accessor/member-reference rewriting, R105 invokes the existing **R104 post-javac type and six-owner-InnerClasses metadata reconstruction**, which in turn **requires R95 to accept all FOUR original nested enum methods and symbolic metadata tables** on the same private output candidate JAR. Only a full R95 acceptance permits final private JAR/report promotion; failures leave no output. The original complete JAR is read-only. No obfuscated identifiers, source literals or proprietary binary are committed.

## Cross-platform Java9 tests

Hosted tests compile a source owner with four enums and two outer-class reads of the fourth enum private String fields. A synthetic original rewrites the compiler-generated accessor identities to independently named methods, preserving linkable outer callsites. The independent candidate retains default javac names and lacks two foreign InnerClasses rows. The R105 pipeline must reconcile the two method declarations, outer references, fourth enum class identity, all four enum methods and all six owner metadata rows, then pass exact R95. An isolated reflection-based Java probe exercises original-like enum methods. Negative tests reject changed enum constants, missing nested enum classes, wrong original hash and noninjective member mappings.

## Noncertification

Passing CI is **synthetic R95 integration proof only**. Actual original v309 R105 private replay requires executing the tool on the separately rebuilt private four-enum Java source candidate (not on the original client runtime). R95 scope is the four nested enums and owner InnerClasses, **not** the original outer owner's 126-field/ten-method Java9 source correctness; R97 complete owner acceptance and original game runtime equivalence remain outstanding.

CLI: `python -m spk_recovery.private_original_synthetic_accessor_rebind_r105 ORIGINAL_V309.jar COMPILED_FOUR_ENUMS_PRIVATE.jar OWNER.class Surrogate NEW_PRIVATE_OUTPUT --original-sha256 ORIGINAL_SHA --candidate-sha256 CANDIDATE_SHA`

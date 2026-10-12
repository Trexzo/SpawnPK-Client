# R104 — single private R98 + R103 post-javac candidate, certified only by R95

## The previously disconnected transformations

R98 already performs safe JVM fourth-enum binary name rebinding but refuses to retain results before R95 checks four exact enums. R103 independently reproduces the original owner's exact six-entry symbolic InnerClasses table while preserving candidate executable bytes. R104 **combines these two operations on one private candidate before invoking R95**. This removes the circular prerequisite and creates a usable all-four-enum acceptance entry point.

## Strict private contract

The tool takes SHA-pinned complete original v309 and independently compiled private candidate JARs, one owner class entry, a noncolliding temporary enum simple name and an output path that does not exist. It requires four original/candidate nested classfiles, exact agreement for the three unchanged enum binary names, the fourth original outer/inner collision, Java class version equality, six exact original ordered owner InnerClasses metadata rows, and no archive duplicate or unsafe entries.

Within a temporary private JAR it uses R98 to rebind all candidate class internal type identities (the fourth enum temporary name becomes the original colliding JVM type). R103 then appends the necessary constant-pool entries and replaces only the candidate owner's class-level InnerClasses metadata with the six original symbolic rows, including both external classes. No original executable method or field bodies are transferred, and all candidate source class method Code remains as separately compiled.

The tool **must run R95** on that single composite temporary JAR against the pinned original; R95 verifies all four nested enum profiles, generated enum member aliases under R49, exact nine-/other-method bodies and all four enum symbolic InnerClasses attributes, plus the owner's complete six-entry table. Only after R95 passes and both JAR hashes remain pinned will R104 publish one private accepted candidate JAR and one sanitized aggregate report.

## Java9 source-based synthetic tests

A synthetic original owner compiled with Java9 contains four enums (fourth initially source-named Placeholder, then re-bound to the legal original binary collision) plus references to two external nested classes: Java-platform Map.Entry and a locally bundled foreign nested class. A separate compiled candidate uses Surrogate as its fourth enum, has all four enum method implementations, but omits the two foreign references so the owner InnerClasses metadata is incomplete. The positive acceptance test requires R95 to pass and all six owner rows and all four enum tables to match. Negatives: changed enum constant, missing fourth quartet, original SHA mismatch. A changed unrelated outer owner method remains **uncertified by R95/R104**, preserving the R97 separation.

## Critical boundaries

Passing hosted tests demonstrates **the integration tool** on synthetic sources. Passing against actual pinned original v309 requires a separately assembled private source candidate with all four nested enums, three from R49 and fourth from R101.1, and private original-jar replay. R104 is **not** R97 complete 126-field/10-method owner acceptance, not original authorial Java source, and not whole-game runtime equivalence. No original JAR, private class/member identities, literals or recovered source are committed.

Private CLI: `python -m spk_recovery.private_all_four_enum_postjavac_acceptance_r104 ORIGINAL_V309.jar FOUR_ENUM_PRIVATE_CANDIDATE.jar OWNER.class SURROGATE_ENUM_NAME NEW_PRIVATE_OUTPUT --original-sha256 ORIGINAL_SHA --candidate-sha256 CANDIDATE_SHA`

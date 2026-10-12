# R103 — recover original v309 owner ordered six-entry InnerClasses metadata

## Original evidence

The SHA-256-pinned original v309 client (`ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`) has exactly six ordered class-level `InnerClasses` entries for the recovered original settings owner: four owner-nested enum classes, including the Java-source-invalid nested simple-name collision, plus two external nested-class references. One external reference belongs to the Java platform and need not be bundled in the original client archive.

R95 correctly requires the complete ordered symbolic owner table, including the two foreign entries and exact JVM access flags; merely compiling four enums need not recreate those external references.

## Private rebuilding tool

`spk_recovery.private_original_owner_innerclasses_rebuilder_r103` takes the original and separately compiled candidate complete JARs with their exact SHA-256 pins and the selected original owner entry. It requires six unique original ordered entries: four local enums, two foreign nested classes and the known self-name collision. It rebuilds ONLY the candidate owner class-level `InnerClasses` attribute, appending necessary UTF8 / CONSTANT_Class constant-pool entries. It never copies any original classfile, field, method Code, constructor or executable bytecode bytes.

The tool preserves candidate field/method binary bytes and all other original candidate class attributes, rewrites no other candidate archive classfiles, reparses the result and requires the exact six-row symbolic tuple (ordering and all flags) to equal the original's. It stages private outputs after hash checks. The aggregate contains counts, hashes and explicit non-certification flags only.

IMPORTANT: A candidate missing three of the four nested enums may pass this metadata-only gate, but it MUST NOT pass R95: owner symbolic metadata alone does not establish packaged enum identities or instruction parity.

## Hosted synthetic Java9 regressions

A Java9 fixture compiles four nested enums, a reference to Java-platform Map.Entry, and a reference to a separate compiled foreign nested class. A second Java9 owner candidate has incomplete metadata and different compiled class inventory. Tests verify ordered six-entry restoration, byte-preservation of unrelated candidate class entries, rejection of SHA mismatches, rejection of incomplete original metadata and existing-output overwrite vetoes. A mutated candidate method must remain mutated after the metadata transform.

## Remaining original acceptance

R103 addresses only the original owner's classfile metadata. R98 fourth-enum binary renaming and R99–R102 source/operand checks are separate. A four-enum private candidate must still be assembled and pass strict R95 all-four method plus nested metadata verification and R97 owner-source Java9 acceptance. Full original runtime equivalence remains unverified.

CLI: `python -m spk_recovery.private_original_owner_innerclasses_rebuilder_r103 ORIGINAL_V309.jar CANDIDATE_PRIVATE.jar OWNER.class NEW_PRIVATE_OUTPUT --original-sha256 ORIGINAL_SHA --candidate-sha256 CANDIDATE_SHA`

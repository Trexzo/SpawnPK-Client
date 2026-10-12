# R106 — exact-original Java 9 case-insensitive enum StackMapTable repair

## New original-v309 discrepancy

A privately rebuilt **all-four-enum** Java9 source candidate, compiled with `javac --release 9 -g:none -proc:none`, matches the pinned actual v309 JAR (SHA-256 `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`) at **25/25 JVM method opcode sequences and 295/295 resolved instruction operands after explicitly controlled generated-field, values-helper and temporary fourth-enum type-name aliases**. The candidate includes four enum classes plus a stub owner; its private candidate JAR SHA-256 is `49f42e864693d362a3d1b15128b933867a5d72e1f33408f035d7883b9610d611`. All original-derived source, binary and string/member identities remain outside GitHub.

Further exact-original inspection exposed a **separate genuine R95 blocker**: in the three-value enum's 25-instruction case-insensitive lookup method, the original Java9 classfile encodes the final StackMap verification frame as `full_frame(offset_delta=5, locals=[], stack=[])` while the new `javac --release 9` candidate uses `chop_frame(offset_delta=5)`. Both have identical Code instruction bytes *except ordinary constant-pool indexing*, opcode offsets, max stack and max locals. The first two StackMap frames are identical symbolically. Both final frames are valid but R95 requires the *original exact frame encoding*.

## R106 strict metadata-only normalization

`spk_recovery.private_v309_enum_stackmap_repair_r106` recognizes the one original six-method/three-constant nested enum with a unique static `(String)->Self` lookup. It requires Java9 class identity, exact 25 method opcodes, an original three-frame source signature (append3, same, full) and the corresponding compiler-generated signature (append3, same, chop). It **constructs** the original's final full-frame representation in the candidate: `ff 00 05 00 00 00 00`, replacing only the trailing `f8 00 05` and adjusting enclosing Code/StackMap lengths. It does **not** copy the original method's Code or StackMap attribute bytes, rename ordinary fields, modify instructions or relax R95.

The tool checks complete-original and complete-candidate SHA-256 pins, verifies **exact preservation of the candidate method Code bytes** and post-rewrite **decoded StackMap frame parity** against the original. It then invokes existing **R105 synthetic accessor-member rebinding → R104 fourth-enum type/owner metadata reconstruction → R95 original four-enum acceptance**, promoting no private artifact unless that entire chain passes. Negative original frame shape and wrong original-JAR pins fail closed.

Private independent local prototype: a +4-byte metadata-only frame rewrite produced the correct three original StackMap frames; isolated execution of the new candidate still passed its enum lookup and accessors. **The official R106 private replay on the actual original JAR and source candidate is not yet certified.**

## Tests and next gates

Real Java9 hosted synthetic fixtures build both original-like and source-candidate four-enum classfiles, inject the source-expected full-vs-chop difference into the original-like *verification metadata only*, and verify R105 fails on the unnormalized candidate while R106 repairs the frame and **requires R95** before acceptance. Tests also exercise actual reflection on the produced candidate, Code bytes preservation, original-frame mismatch rejection and SHA-pin mismatch rejection.

This is a **four-nested-enum source/metadata parity** repair; it does not certify original outer owner's 126 fields, ten methods, R97 owner source compilation, original client execution or full gameplay runtime equivalence. No proprietary binary, string literals or recovered original member identifiers are committed.

CLI: `python -m spk_recovery.private_v309_enum_stackmap_repair_r106 ORIGINAL.jar FOUR_ENUM_SOURCE.jar OWNER.class SURROGATE_CLASS NEW_PRIVATE_OUTPUT --original-sha256 ORIGINAL_SHA --candidate-sha256 SOURCE_SHA`.

# R116 — original-v309 364-instruction saver: metadata-only full-frame recovery

## Actual original and recompiled source evidence

Pinned read-only original complete client SHA-256 `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`; independently Java9-source-recompiled full owner candidate SHA-256 `dcf1e51cde2c8720bde22b4f43899d65e44766adbc2fab905b76fb7f58ccfb3c`. The original 364-instruction private static saver and compiled source have 364/364 exact JVM instruction opcode and normalized operands, nine matching branch-target ordinals, one identical typed exception handler and 929-byte Code with max stack=6 and max locals=3.

**Corrected original saver StackMap count:** both source and original have **10** frames. The only original-vs-source frame metadata difference is frame #2: original `full_frame(offset_delta=308, locals=[top, java/io/BufferedWriter, integer], stack=[])`, while source compilation emits `append_frame(2)(offset_delta=308, appended_locals=[java/io/BufferedWriter, integer])`. Remaining nine frames match in type, offset and symbolic verification types. This corrects an earlier exploratory read across an adjacent method which incorrectly counted 12 candidate frames.

## R116 repair

`spk_recovery.private_v309_saver_one_fullframe_rebind_r116` selects the **unique original 364-instruction private-static void method** from the SHA-pinned complete original JAR. It parses the original and candidate Code attribute and exact ten original Java9 StackMap frames; requires all other original frame shapes, positions and object verification types to match. The only accepted candidate mismatch is the known second-frame append2 encoding. It **constructs**, without copying original Code or original constant-pool bytes, the 12-byte `full_frame` representation using the candidate's own verified `java/io/BufferedWriter` class constant-pool entry, replacing the candidate's 7-byte append2 frame (**exactly +5 metadata bytes**). It adjusts StackMapTable and enclosing Code attribute lengths and leaves all candidate executable `Code` bytes and other method bodies untouched.

R116 then invokes the existing strict **R113→R66/R81** pinned-original saver gate against the *new* repaired SHA-pinned candidate JAR, requiring every original saver JVM operand, all 10 symbolic StackMap frames and the ordered original exception region before publishing a private postimage JAR and sanitized JSON. Original JAR and rebuilt source are never committed.

### Independent local proof

Against the actual original and private source-compiled candidate, a separate read-only classfile script performed precisely the five-byte expansion and verified the original ten frame encoding types. The patched private candidate JAR SHA256 is `58a59de4f8ab62cd80a27b34803ee056a3dbb9450fd000f21d53779b8dc7f4b6`; the 929-byte saver Code SHA256 remained `d8c619f44812162f898494d72d207ec66994ad7de9b2e2dedafec2020251abe8`. Running a **Java 21** `-Xverify:all` isolated probe against only the repaired *candidate* (never the original JAR), with `Class.forName(..., false, ...)`, loaded and resolved the candidate saver/loader method metadata successfully without class initialization or original-game execution.

The independent private script does **not** itself execute the GitHub R116 full R113 chain; hosted tests are synthetic classfile metadata and mocked R113 integration. The official pinned original private CLI replay remains pending.

## No broader certification

Only the saver second frame is repaired. The original 697-instruction loader still has 161 ordinal-aligned StackMap frames with four category and two explicit-local payload differences; R114 preimage is not full loader verifier parity. Fourth-enum name/accessor and two original initializer callsite identities remain to be rewritten before R95/R58/R107. External helper behavior, filesystem/callback/gameplay runtime and whole-client equivalence are unproven.

Private CLI:
`python -m spk_recovery.private_v309_saver_one_fullframe_rebind_r116 ORIGINAL.jar JAVA9_SOURCE_CANDIDATE.jar OWNER.class NEW_PRIVATE_OUTPUT --original-sha256 ORIGINAL_SHA --candidate-sha256 SOURCE_SHA`.

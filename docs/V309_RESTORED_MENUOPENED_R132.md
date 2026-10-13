# R132 — second independently recovered v309 Java source candidate

## Real source added to the GitHub client tree

`source-candidates/v309/src/rs/runelite/events/MenuOpened.java`

The user's uploaded decompiled source was not yet original-JVM-equivalent: its generated `equals(Object)` compiled a direct `ireturn` after `canEqual(this)` where the exact v309 client used explicit conditional false/true returns. R132 restores the original control flow and readable local/parameter names, then compiles **only the Java source** under Java9 using empty project classpath/sourcepath. No original `rs/` classfiles serve as dependencies and no original executable Code bytes are imported.

The original read-only v309 client SHA-256 is `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`.

| Measured source-recovery evidence | Exact private result |
|---|---|
| Restored Java source SHA-256 | `bf7908561ce437099912fbad55e1a9e7e0bdabd8afae56cd3c28bd5fc622fef9` |
| Source and original classfile version | 53 (Java 9) |
| Original class methods, fields | 5 methods, 0 fields |
| JVM method instructions, PCs, resolved operands | **33/33 equal** |
| Frozen normalized original JVM opcode/operand witness | `4b8ff0ac0750b72b766398f080ec4443c813af77cfb2cb66746cecee07e526ad` |
| Original equals StackMapTable | Three frames, raw `00030708f9000e` |
| Source-built equals StackMapTable before rebind | Three frames, raw `00030708fc000e070007` |
| Postjavac repair | Re-encode only third verifier frame `append_frame` to original `chop_frame`, correct StackMapTable and Code attribute lengths, preserve executable Code |
| Repaired source-compiled class SHA-256 | `161d720a28dffdd09060909e69bc50ada0ccf5409d6db476b85a45597bfd14cf` |
| Isolated source-built JVM verifier | **Passed `-Xverify:all`**, reflexive equals and `toString()` smoke |
| Original client code copied or original JAR executed | **No** |

These metrics are from a local read-only exact-original-v309 method comparison and an independently compiled class. They do not certify authorial Java identity or an entire client. The original source file, original classfile and private compiled postimage are **not** imported as binaries into GitHub.

## Scalable verified event-family repair

R131 supplied one tightly scoped metadata rebind for `rs/runelite/events/ClientStartUp`. R132 expands that implementation to **two independently proven owners only**, adding `MenuOpened` to the explicit allowlist. Every source-compiled preimage must have exactly the recorded Java9 owner, declaration inventory and verified `equals(Object)` StackMap append preimage; the repaired frame is checked and **all executable Code bytes must remain identical**. A different or unreviewed class is rejected. R131's original tests continue to pass unchanged.

R132 Ubuntu and Windows CI compile the **actual committed MenuOpened Java source**, compare its normalized instruction transcript with a frozen original-v309 hash, run the proof-constrained StackMap rewrite, check no executable Code changes, and load the independently rebuilt class under `java -Xverify:all`. No original client binary appears in hosted CI. The existing R131 source and tests remain covered by full Recovery CI.

## Status and source publication policy

This adds a **second real client Java file** to the provisional `source-candidates/v309/src/` tree, not the canonical complete `recovered-source/v309/src/`. This provisional directory lets the user and other GitHub workstreams work with actual source files as soon as each is independently verified, without misrepresenting a two-class snapshot as a complete, runnable SpawnPK client.

The remaining client-only source work is broad: original-to-source class/member lineage for the other v309 classes, dependency-island completion, source AST rewrites, Java and Windows namespace legality, zero original binary-fallback whole-client compilation, runtime assets and isolated client testing, and eventually a complete Source Milestone release (issue #1004). No independent server reconstruction belongs in this workstream.

# R117 — exact original 161 loader StackMap verification *states* at Java9 compiled instruction positions

## Actual original-v309 independent private proof (2026-10-13)

Original complete client JAR pinned SHA-256: `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`. Separately reconstructed Java9 full-owner candidate JAR SHA256: `dcf1e51cde2c8720bde22b4f43899d65e44766adbc2fab905b76fb7f58ccfb3c`; R116 saver-only five-byte metadata repair produces private candidate JAR SHA256 `58a59de4f8ab62cd80a27b34803ee056a3dbb9450fd000f21d53779b8dc7f4b6`.

The original and source-recompiled 697-op loader match every normalized JVM opcode/operand, all 120 branch target instruction ordinals, 44 typed handler ordinal ranges, 78 ordered static field writes, stack=4 and locals=6. Java9 recompilation makes 86 originally narrow `ldc` instructions wide, so the 161 original StackMap byte offsets and compact frame-type bytes cannot simply be copied unchanged. The R114 preimage explicitly identified **four frame-category differences, two explicit local payload differences, zero stack payload differences**, while 161/161 StackMap frame *instruction ordinal destinations* match.

Using an independent **private, read-only-original** classfile parser, reconstructed all **161 original frame verification kinds, append/chop arities, explicit original locals, stack object types and corresponding `uninitialized` new-sites** at the separately compiled candidate's JVM instruction offsets. Object verification types are encoded using **only candidate constant-pool class entries**; no original Code, classfile or CP bytes are inserted. The patched candidate loader has identical 697 executable JVM Code bytes (SHA256 `e7644b2efbeef959de60d40a6a29890ae5fe56c75285a2cf06dfb29e46389b49`), its rewritten StackMapTable is four bytes shorter, and its 161 frame states match the original **symbolically at ordinal-aligned PCs** (literal compact frame_type byte values necessarily differ where `ldc_w` changes instruction widths). The resulting combined original-saver+loader metadata candidate JAR SHA-256 is `31c5fd94cd5be767d950eac4ff4d58a47e57389d36b82eee9b56ce98911d1d5e`.

An isolated Java 21 `java -Xverify:all` probe of **only the newly compiled candidate**, with `Class.forName("rs.f.a", false, ...)` and reflective method inspection, passed without class initialization. The original client JAR was **never executed**. Source compilation includes nonoriginal dependency stubs, so this only establishes that the bounded reconstructed candidate classfile passed JVM verifier checks.

## R117 GitHub source-recovery tooling

`spk_recovery.private_v309_loader_symbolic_frames_r117` requires complete independent original and source-candidate SHA256 pins, the unique 126-field/ten-method original owner, and the unique 697-op loader. It first demands the already separately proven **R113 saver** on the input (364 executable JVM operands, ten original StackMap frames exactly), followed by strict **R66/R81** all 697 loader JVM symbolic operands, all 120 branches, all 44 typed exception regions and all 78 static writes. No failing binary may reach metadata rewriting.

It then detects the **known four encoding-category and two local-payload source preimage differences** with 161 matching frame ordinal destinations. It reconstructs original verification frame **states** at the post-javac compiled instruction PCs; chooses legal short/extended same or one-stack forms according to new offset deltas, remaps every object verification type into the independently compiled candidate constant pool, and maps uninitialized allocation PC references to their corresponding new instruction ordinal. It alters only the loader `StackMapTable` and its enclosing `Code` attribute length; the entire executable `Code` bytes and all other method bodies/attributes are preserved.

On the new postimage JAR, R117 **re-runs R113** and R66/R81, parses every rebuilt frame using the existing Java9 classfile verifier and requires all **161 original symbolic frame states** at identical instruction ordinals, including explicit locals and stack. Only on full success does it privately promote the compiled postimage and sanitized aggregate JSON. Failure leaves no output. No original client source, binary names, string constants or classfile bytes are committed.

Hosted synthetic tests check 161 original frame symbolic transformations, Java9 compact/extended offset rebinding, missing CP class veto, changed locals, wrong category, misaligned frame site, missing 161 frames and safe uninitialized NEW-site mapping. They are fixtures, **not original-v309 replay**.

## Boundaries

R117 is a bounded *large-method classfile verifier parity* gate, not proof of exact original raw `frame_type` bytes (which cannot always match when source changes LDC widths). Nor does it certify original Java authorial source identity, external helper behavior, filesystem and callback side effects, original fourth-enum class/member identity, R95 all-four-enum acceptance, R58 all 93 initializer operands, R94 complete nine ordinary methods, R88 exact final declarations, R107 complete owner, or gameplay/runtime equivalence.

Private CLI:
`python -m spk_recovery.private_v309_loader_symbolic_frames_r117 ORIGINAL_V309.jar POST_R116_SAVER_JAVA9_CANDIDATE.jar OWNER.class FRESH_PRIVATE_OUTPUT --original-sha256 ORIGINAL_SHA --candidate-sha256 SOURCE_SHA`.

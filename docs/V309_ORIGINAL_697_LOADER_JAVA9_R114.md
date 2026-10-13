# R114 — original-v309 697-instruction Java9 loader: R66/R81 and 161-frame preimage frontier

## Independent actual-original 2026-10-13 findings

Read-only complete original `client(7).jar` SHA256 `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38` and separately source-recompiled PRIVATE Java9 candidate JAR SHA256 `dcf1e51cde2c8720bde22b4f43899d65e44766adbc2fab905b76fb7f58ccfb3c` were compared by independent `javap -p -v -c` and instruction/exception/stackmap parsers (original JAR never executed).

Original and candidate owner 697-instruction public-static-void method agree on **697/697 opcode identities (after Java9 compiler LDC width choices), all 697 normalized symbolic operands, 120/120 branch target instruction ordinals, 44/44 typed exception-handler ordinal ranges, 78/78 static writes, and original max_stack 4/max_locals 6**. The rebuilt source chooses wider `ldc_w` for **86 original `ldc` sites**. This is a bounded *preimage* method structural/operand proof, not byte-identical original Code.

### Original-vs-candidate StackMap difference — do not conceal

Both methods have **161 StackMapTable frames**, all **161 at exactly corresponding JVM instruction ordinals**, even though byte offsets differ because of source compilation width changes.

| Verification-frame feature | Compared | Mismatches |
|---|---:|---:|
| Frame position at instruction ordinal | 161 | **0** |
| Frame encoding category (same/stack1/appendN/chopN/full) | 161 | **4** |
| Explicit local-variable payload | 161 | **2** |
| Explicit operand-stack payload | 161 | **0** |

The two differing local payloads include one `full_frame`'s locals and one `append` frame's locals; four encode different append/chop categories. These are **real verification metadata differences**, not safely dismissible CP renumbering. R114 explicitly reports **R114_exact_original_StackMap_encoding_accepted=false** and **R107_complete_owner_accepted=false**. Future original-frame recovery must preserve legal verification state and revalidate the resulting source-compiled classfile; it must not copy original executable Code bytes or weaken strict original parity.

## R114 SHA-pinned private preflight

`spk_recovery.private_recompiled_v309_loader_preimage_r114` requires complete separate original/candidate SHA-256 pins, identical Java9 owner class identity, R112's exact 126 fields and ten original methods, the unique original 697-op `()V` public-static method, and exact 4/6 JVM stack/locals. It calls existing **R66→R81** *before* any StackMap observations, requiring all 697 original JVM instruction operands, 120 explicit branches, 44 ordered typed handlers, 78 own writes and original invokedynamic evidence. It then compares every frame's bytecode offset **through its own method's decoded instruction-ordinal map**, never numeric byte offsets alone, and requires the independently observed current source-preimage frontier of 4 frame-category differences, 2 explicit-local payload differences, and zero explicit-stack payload differences. It publishes only a sanitized private aggregate, no altered or accepted JAR.

Hosted tests use synthetic profile fixtures for the genuine pinned-original method sizes/StackMap mismatch and negative cases for original pin, missing frame, misaligned frame, altered category/payload, changed source identity and R81 failure. A separate actual-`javac --release 9` fixture independently compiles **two 697-instruction Java methods** and exercises the real existing R81 operand comparator. Hosted CI does **not** have the original pinned JAR and is **not** proof of actual-original execution or method authorial source.

## Remaining acceptance

The 364-instruction saver source has a separate R113 gate; R114 does not certify its 10 StackMap frames or the whole ten-method owner. The four nested enums require post-javac R106/R105/R104/R95 (original 4th enum is source-illegal). The complete owner requires **R94 + R58 + R88 + R107** against **the same final SHA-pinned postimage**. All must pass before any whole-owner acceptance claim. Original filesystem/helper behavior, callback side effects and actual client/gameplay runtime equivalence are unproven.

Private CLI:
`python -m spk_recovery.private_recompiled_v309_loader_preimage_r114 ORIGINAL.jar SOURCE_CANDIDATE.jar ORIGINAL_OWNER.class NEW_PRIVATE_OUTPUT --original-sha256 ORIGINAL_SHA --candidate-sha256 SOURCE_SHA`.

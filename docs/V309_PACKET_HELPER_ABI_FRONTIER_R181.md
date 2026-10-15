# R181 — original v309 Packet helper ABI and source-recovery frontier

This client-only, read-only workstream follows [R179 #1070](https://github.com/Trexzo/SpawnPK-Client/pull/1070) and milestone [#1004](https://github.com/Trexzo/SpawnPK-Client/issues/1004). It does not recover or publish original-derived code.

## R179 verified state and missing source

R179 reports independent private Java9 source recompilation and original JVM method-Code comparison for Packet owner rs/x/e: 80 ordinary methods plus its static initializer, 2,296/2,296 decoded instructions and 11/11 original field identities. The verifier requires fully source-recovered parent classes rs/a and rs/t, but compiles with four signature-only, **unverified-body** Java helper classes:

- rs/q/a
- rs/v/a
- rs/h
- rs/f/a

The 1,279-file private candidate from R179 still reports **2,343 JDK-only compilation errors**. R179's +4 change is not an improvement, and the provisional external-binary-capsule 516-error result is not comparable.

## New R181 reproducible audit

Run the module spk_recovery.private_v309_packet_helper_frontier_r181 against the private exact original JAR. It requires original-v309 JAR and Packet class SHA256 pins, exactly one classfile per helper, reads each original class without executing it, and produces:

- Original helper class SHA256, classfile version, field/method counts, JVM instruction counts.
- Distinct direct Packet-to-helper method invocations and field accesses with direct declaration matching counts.
- Packet field/method descriptors mentioning each helper type.
- SHA256 of a private complete original member/call/descriptor worklist.
- Optional exact-SHA-pinned private candidate ZIP presence check for the recovered-source/v309/src/<owner>.java path. Presence is never taken as evidence of equivalence.
- Optional separate expected helper class SHA256 manifest for stronger cross-workstream handoff.
- An opt-in private-name inventory; the default output gives counts and digest rather than original member names.

Basic private invocation:

    python -m spk_recovery.private_v309_packet_helper_frontier_r181 PRIVATE_ORIGINAL_V309.jar FRESH_PRIVATE_R181_REPORT.json

Optional private candidate cross-check:

    python -m spk_recovery.private_v309_packet_helper_frontier_r181 PRIVATE_ORIGINAL_V309.jar FRESH_PRIVATE_R181_REPORT.json --source-candidate-zip PRIVATE_1279_SOURCES.zip --source-sha256 EXACT_SHA256 --private-names

Evidence boundary: this is a direct invocation, field-access and declared-descriptor census. It does not prove closure for reflection, invokedynamic, inherited members, generics, StackMap frames, class allocations without direct invocation or runtime resolution. Nor does it compile the helpers, recover source, add stubs, change the compilation frontier or authorize redistribution.

## CI and next private action

Ubuntu/Windows hosted tests compile synthetic Java9 Packet-like and helper sources with no SpawnPK original classes, binary or decompiled code. They check SHA enforcement, original owner/classfile uniqueness, direct call and field counts, deterministic worklist identity, opt-in private detail, private candidate presence without acceptance, and fail-closed negative tests.

Run R181 privately on the original pinned JAR and private 1,279-file tree, prioritize helpers from the actual class/member worklist, reconstruct independently verified helper source from original JVM evidence and rerun same-toolchain empty-project-binary-classpath compilation. Neither the helper methods nor the complete v309 client are recovered by this tool.

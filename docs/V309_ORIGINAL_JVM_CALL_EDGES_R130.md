# R130 — exact original-v309 JVM invoke-edge extraction

## Purpose

The canonical deliverable remains a fully deobfuscated, independently compiled **client-side** `recovered-source/v309/src/` tree ([#1004](https://github.com/Trexzo/SpawnPK-Client/issues/1004)). The merged R127/R128 tools produce 501 structurally unique but **unaccepted** source/JVM candidate mappings; matching source literals add evidence for a subset. R129 [#1013](https://github.com/Trexzo/SpawnPK-Client/pull/1013) can classify outgoing owner-call overlap, but did not independently extract original JVM edges.

R130 supplies that **original bytecode side**, in a private read-only tool. It independently SHA-pins the v309 original to `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`, validates archive safety (duplicate member, traversal, symlinks, entry counts), and parses every `rs/*.class` through the repository's established `bytecode_profile.profile_class_field_accesses` classfile decoder. No classloader, JVM client launch, connection to SpawnPK servers, decompiler execution, or original binary modification occurs.

For each original JVM method it counts *direct* `invokevirtual`, `invokespecial`, `invokestatic` and `invokeinterface` instructions whose constant-pool-resolved owner is itself in the `rs/` game client namespace. Counts are aggregated into owner-to-owner directed edges, matching R129's `caller/callee/count` private evidence schema.

**`invokedynamic` is explicitly excluded from attributed owner edges** and counted separately: the invokedynamic instruction does not expose a directly trustworthy callee owner without separately resolving its BootstrapMethods/MethodHandle and lambda lowering. Other bytecode uses, method descriptors, reflection, field accesses, dynamic proxies and runtime dispatch are not treated as calls. No source↔original identity is inferred by counting calls.

## Private replay

```text
python -m spk_recovery.private_original_jvm_call_edges_r130 \
  PRIVATE_ORIGINAL_V309.jar FRESH_PRIVATE_JVM_EDGES.json
```

By default the resulting JSON contains only SHA-256 pins, aggregate counts, dispatch categories, excluded invokedynamic count, and the SHA-256 digest of the private edge inventory. No class names or method signatures are printed.

Use `--private-edges` **only locally** when preparing the private R129 evidence envelope; that adds `private_original_call_edges`. The report must stay outside public GitHub and outside the user's shared source tree. An optional `--original-sha256` override is for pinned **synthetic fixtures**, not to weaken real-original acceptance.

## Validation and next gate

Synthetic CI compiles three actual Java 9 classfiles containing static/virtual/interface calls and one lambda. The tests verify the original-constant-pool owner edges, explicitly omitted `invokedynamic`, class/method inventory, pin mismatch, duplicate ZIP names, ZIP-slip, symlinks, malformed classfile veto, and no private identifiers in public output. Both Ubuntu and Windows must pass.

R130 is only **half** the independent input required by R129. Next implement a source-side JDK Trees/Elements `MethodInvocationTree` collector with resolved declaring owners, explicitly refusing unresolved or ambiguous symbols. For the existing 1,271-file decompiled candidate, full symbol attribution may fail until dependency imports and Java name collisions are repaired. Those limitations must be surfaced, never filled by heuristic text matching. Only then may R129 consume two independently pinned parser inventories.

**Not certified by R130:** original class/member lineage, resolved method operand equality, behavior/runtime equivalence, whole-client compilation, complete deobfuscation or source publication. No independently authored server code is in scope.

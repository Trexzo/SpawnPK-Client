# R112 — original-v309 364/697 method source recovery frontier

R111 (merged) proved seven independently Java9-recompiled original ordinary owner methods (**74 instructions**) on a private partial 126-field source candidate. The two missing bodies contain **364** and **697** original JVM instructions. The existing partial candidate has a **one-op stub** for the first and completely omits the second; these placeholders are never accepted as parity.

`spk_recovery.private_large_owner_methods_inventory_r112` performs a **read-only** inventory on the complete, exact SHA256-pinned original v309 client JAR. It requires the original 126-field, ten-method Java9 owner, verifies the unique method counts `2,2,2,3,4,20,41,213,364,697`, finds exactly one ordinary `()V` method of each large length, and checks branch target alignment and symbolic field/call/indy operand availability.

For each original 364/697 instruction method it records instruction-count, branch sites, invocation and invokedynamic sites, fields read and written, returns, switch sites, typed exception handlers, maximum stack and locals, and a checksum of its private operand map. Full symbolic member identities and decoded bytecode rows are written **only to an on-machine private manifest**, never logged to hosted CI or committed. The sanitized JSON includes counts, boolean noncertification flags and hashes only; fail-closed mismatch and an occupied output prohibit promotion.

Hosted fixtures are deliberately synthetic (126 fields, the known ten method counts) and mutate missing owner fields, large method opcode length, branch destination, invokedynamic bootstrap index, unresolved member descriptor and missing return. They test contract safety, **not actual original-v309 method body recovery**.

**Remaining work:** recover Java source for the original 364-op and 697-op methods, validate exact JVM operand/handler/control-flow parity with R86/R87, eliminate the one-op stub and both extra source-only outer accessors, and then run the final R106→R105→R104→R95 plus R94/R58/R88/R107 on the same pinned owner candidate. Original helper functionality, filesystem/configuration writes, and whole client gameplay/runtime equivalence remain unproven.

Private CLI: `python -m spk_recovery.private_large_owner_methods_inventory_r112 ORIGINAL.jar ORIGINAL_OWNER.class NEW_PRIVATE_OUTPUT --original-sha256 ORIGINAL_SHA`.

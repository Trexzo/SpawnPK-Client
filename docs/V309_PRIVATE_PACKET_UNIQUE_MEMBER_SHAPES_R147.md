# R147 — deterministic original Packet JVM → decompiled Java member *seeds*

Client-only work continuing [R146 #1033](https://github.com/Trexzo/SpawnPK-Client/pull/1033) and [source milestone #1004](https://github.com/Trexzo/SpawnPK-Client/issues/1004). We are now moving **below the source-class mapping level**, toward individual original JVM method/field identity recovery.

A real private analysis of the exact SHA-pinned original-v309 `rs/x/e.class` and the candidate `rs/io/Packet.java` (the class with the R146 full 91/91 structural member correspondence and both exact RSA literals) identified **20 original-to-source member pairs whose complete access+erased descriptor+declaration-kind key occurs *exactly once* on BOTH sides**:

| Member identity kind | Unambiguous by full shape | Withheld as structurally ambiguous |
| --- | ---: | ---: |
| Fields | **6** | 5 |
| Constructors | **2** | 0 |
| Ordinary methods | **12** | 66 |
| **Total** | **20** | **71** |

These candidate seeds are deterministic **structural matches only**. They do not prove name equivalence, original owner method bytecode parity, callsite semantics, identical field values or correct behavior. In particular the repeated `public int method()` erased shape occurs **37 times** in this owner; assigning those names by order or similarity would be irresponsible. Original Java method correspondence still needs bytecode, method/body signatures, distinct original call edges and verified runtime context.

## GitHub implementation

1. SHA-pin the complete exact-original JAR and complete Java source ZIP. Invoke R146's independent **whole-owner** gate first. If its field/method 91/91 multisets or exact RSA literals don't correspond, **R147 refuses all member seeds**.
2. Parse original JVM member descriptors/access and original binary member identities with the existing trusted `parse_class` parser, explicitly distinguishing `<init>` constructors from ordinary `void` methods; ignore JVM `<clinit>` source initializer scaffolding.
3. Independently parse the unchanged real candidate Java with a JDK `JavacTask.parse()` helper, retaining every field/method/constructor's *private* source identifier and same access+erased type signature. Verify multiplicities of every key on both sides before preparing any mapping.
4. For each group where exactly one original member and one source member have that signature, emit a provisional **one-to-one mapping candidate**. If two or more members share a shape, withhold **every** member in that group. Prohibit sequence/order/name heuristics, arbitrary tie breaks and inventing original member behavior.
5. Write only a sanitized aggregate SHA/count report by default. An optional `--fresh-private-identifier-map` explicitly writes identifier-bearing candidates to a **fresh local private file**, never to public GitHub/Actions. Original client classes, Java source, the source-to-original name map and method code never leave the isolated workspace. Both original hashes are reverified after read-only processing.

Exact-private invocation:

```text
python -m spk_recovery.private_v309_packet_member_seeds_r147 PRIVATE_ORIGINAL_V309.jar PRIVATE_SOURCE_CANDIDATE.zip FRESH_PRIVATE_COUNTS.json --source-sha256 2f9903b5eb9c89eb736f806e0cbd0aa468e4cd2408eb436ec3fd03d3094e4536
```

The pinned original v309 JAR SHA-256 defaults to `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`. If a private member identity candidate map is explicitly needed, add `--fresh-private-identifier-map /private/output/new-member-candidates.json`; never commit that output.

## Hosted evidence and limits

The Ubuntu/Windows synthetic test builds independently compiled original Java classfiles and an otherwise corresponding source class with different names. It includes intentionally duplicate source and original no-argument int-returning methods; the tool must leave *both* ambiguous while selecting exactly unique fields/methods/constructors. Changed method signatures or different RSA sentinel bytes must abort upstream at R146. No original game client file, source or identifier-bearing map is sent to hosted CI.

**Next:** prioritize the 20 unique-shape candidates for independent original method bytecode and call-edge parity using existing project verifier infrastructure, and map the remaining 71 through actual evidence. Only then can matrix source code safely bind to verified original Packet methods through [R145](https://github.com/Trexzo/SpawnPK-Client/pull/1032). Final v309 Java compilation errors remain **516**, with no new original client runtime/code-identity acceptance implied.

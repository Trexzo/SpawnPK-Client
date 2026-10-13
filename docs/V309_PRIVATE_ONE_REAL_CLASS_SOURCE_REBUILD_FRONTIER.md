# First independently recompiled original-v309 client source class — private bounded acceptance frontier

This is a private original-client **Java source recompilation experiment**, separate from synthetic hosted CI. It demonstrates the type of per-class evidence ultimately required for `recovered-source/v309/src/`; it **does not** certify the entire client or original authorial source.

## Real original and source candidate

- The independently hashed original v309 JAR is pinned to SHA256 `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38` and was opened read-only, never launched.
- From the separate private 1,271-source Java candidate, one **standalone, JDK-only** utility class was selected. Its class identity was independently matched to an original classfile of the *same binary name*, with structural source/JVM singleton and literal evidence. Original obfuscated field/method names were privately restored from the directly observed member bodies (no speculative gameplay).
- The source was compiled in an isolated empty dependency/classpath/sourcepath with `javac --release 9 -g:none -proc:none`. **No original `rs/` classfile** or project JAR was used to satisfy javac. The source, separately compiled JAR and original class slice remain private.

## Original vs independently source-compiled evidence

| Gate | Actual observation |
|---|---|
| Original and compiled JVM class version | **53 / Java9 on both** |
| Method bodies (constructor, utility entry, four helpers, initializer) | 7 |
| Total ordered JVM instructions | **79 / 79** |
| Ordered opcode, byte offset and resolved symbolic operand equivalence | **79 / 79 exact** |
| Field and method declaration descriptors | Identical |
| Original `max_stack`, `max_locals`, JVM argument sizes | **All seven method Code headers identical** |
| Original StackMapTable entries | 14 |
| Source-compiled initial StackMap category differences | **One**: original first `chop_frame` vs javac `same_frame` |
| Post-javac metadata-only rebind | Change that one frame encoding; length fields increased by 2 bytes; no executable Code bytes copied or changed |
| Repaired StackMapTable categories, offset delta and explicit payloads | **14 / 14 original entries equivalent** |
| VM verifier / isolated behavior | Rebuilt class independently loaded using `java -Xverify:all` and its inspected JDK-only entry point ran successfully |

The source-compiled preimage SHA256 was `ac650cf92809da91def4e15e717a09a4bcff58ae889f9de9e8c1d21a7fc038b8`; after the two-byte frame-encoding expansion the private classfile SHA256 was `b380765239dd20eb88948b8cae4d1084a985ae19de35b672135436021b0a5055`. These are **derived private evidence identifiers**, not an acceptance checksum equal to the original JAR or client classfile.

The initial naïve one-byte frame-type replacement produced malformed metadata (fewer frames visible) despite a successful class load, and **was rejected**. The accepted research candidate uses the correctly encoded `chop_frame` (including `offset_delta=26`) and updates **both** the nested StackMapTable attribute length and enclosing Code attribute length. The final bytecode and all 14 frame metadata entries were independently inspected against original `javap -v` output, then the corrected source-built class was loaded/verified with the JVM.

## Boundaries / remaining work

This proves a **real, standalone per-class source-rebuild parity experiment** with original JVM operands and corrected verification metadata. It does not prove full binary byte identity, the original Java author's source formatting, a 1,159-class source tree, all linked dependencies, client UI/render/cache/gameplay semantics, production network safety, or the ability to compile the 1,271-source workspace. It also does not yet constitute a general automated R129 verifier-frame repair tool or a Source Milestone publication.

Next: generalize this class-level rebuild and verifier-metadata-only rebind under the existing R25/R32/R66/R81/R116/R117 proof components; choose additional high-confidence R127/R128 source↔binary pairs; preserve source/member logical IDs; then clean-compile from Java with zero original-client binary fallback. All original-derived Java, binary class slices and raw private identities remain outside this public GitHub PR. Only verified aggregate counts and provenance digests are published.

This work is **client-only**. No independently implemented server source was involved.

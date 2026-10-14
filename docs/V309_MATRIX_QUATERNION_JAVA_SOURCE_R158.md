# R158 — original v309 matrix quaternion Java source reconstruction

CLIENT-only original SpawnPK source recovery, stacked on R157 #1048, milestone #1004. Original proprietary binaries and source fragments stay in private workspace.

## Actual private original method evidence

Original v309 matrix class com/a/b/a/b.class SHA-256: 52b1d1bf805643aefb9244a88fbf6b47b67b36664d920e023db3d68afa4e3030. Whole original v309 JAR SHA-256: ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38.

Independently reconstructed the original public quaternion-to-rotation matrix method a(com/a/b/a/c):void as Java9 source. It uses the original quaternion input's four float fields, retains the ten original float products and the order of all nine 4x4 matrix rotation assignments, without changing floating-point associativity. Java9 javac with empty original/project/external binary classpath emitted **160/160** original bytecode instructions with exactly matching offsets and resolved original class/member field references. Original quaternion class c is represented only by a Java **compilation-only source scaffold**; its behavior is not accepted as recovered.

One new PRIVATE original-name matrix Java source was compiled with three PRIVATE source-only helper Java classes a, c, e, no original binary fallback. All six selected original matrix method instruction lists matched the original JVM:

| Member | Decoded original JVM instructions matched |
| --- | ---: |
| Internal Euler decomposition c():float[] | 108/108 |
| Alternative decomposition d():float[] | 113/113 |
| Original 4x4 toString():String | 60/60 |
| Transform-component writer a(com/a/b/a/a):void | 93/93 |
| Vector scale extraction i():float[] | 68/68 |
| Quaternion rotation a(com/a/b/a/c):void | 160/160 |
| **Six-member source-only bundle** | **602/602** |

The six-member source file was compiled once as a class with the three helper Java sources. A private javap full decoded instruction tuple comparison proves these exact method offsets/opcodes/CP-resolved references. The formatter's direct self-calls to c() and d() both have separately verified source implementations, no callsite-only stubs.

Exact private source ZIP SHA-256: 29e4ae8192fde64775127859d36ebb19e43b9b1baa784113e54396deff6a2be1.
Three helper source ZIP SHA-256: fc1939737d32ad1cae46011e0166ccf71c029bccf6431653eef1f6ff3ab2427b.
Six-method selection JSON SHA-256: 56b69a815430e1b243c6fb818856d899151ceae4eb0b9adf571e60fc36bbb6e3.

## New GitHub acceptance step

The R158 private verification wrapper calls R150/R155/R156 source-only original class verifier with exact whole-JAR, source, helper and selection pins, and demands the original matrix class digest, precisely six selected original methods, 602 matching original instructions, three Java-only helper files, exact closed two self-call edges and zero original binary classpath fallback. Helper source implementations are never marked original. StackMap metadata parity is reported independently. Complete matrix runtime, full original code attributes, complete v309 client javac compilation, third-party dependency provenance and source publication rights remain unaccepted.

Cross-platform synthetic Ubuntu and Windows tests compile an rs/Game-linked matrix with three other original helper types and separately compile six corresponding selected Java method implementations with *only* three helper Java sources. Negative tests mutate quaternion operators, remove a helper and alter expected opcode counts. R157/R155 regression tests rerun. No original source or binary enters public GitHub or CI.

The original source evidence was independently reproduced using private javac and javap. **Exact GitHub R158 module replay on the real private archives remains a separate outstanding acceptance check**, not automatically established by the above independently compared instructions.

Cumulative privately reconstructed matrix source now covers **19 of 24 original matrix JVM members and 952/952 matching instructions** (R157 18/792 plus R158 quaternion 160). Five methods remain: two Packet-dependent constructor/decoder and three other non-Packet matrix math operations. The original whole-client compiler frontier remains 516 previously measured errors, no new full-project compile is claimed.

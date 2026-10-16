# R220 — cross-batch v309 spellbook original-source closure preflight

All individual original JVM Code bodies for `rs/n/c/ap` are reported as recovered from the existing readable `rs/interfaces/widgets/Class179.java` across R212–R219, but the eight batches were compiled separately against different compiler-only helper declarations. **They have not yet been compiled in one class.**

This batch adds an executable Python consistency gate that imports the actual R212–R219 source verification modules and requires (i) exactly 14 original JVM method identities, (ii) no method duplicated or omitted, (iii) original instruction counts per method and **4,314** in aggregate, (iv) correct original-method ownership by each independently reviewed PR batch, (v) original parent class SHA-256 consistency, (vi) existing readable source SHA-256 consistency where modules expose it, and (vii) explicit flags for the two compiler-normalized source bodies: long filter method (R214) and ancient layout (R217). Mutated manifests, duplicate/missing methods, wrong op counts and undocumented normalizations fail closed.

## What this gate does *not* establish

It does not compile the full readable `Class179.java` together with the recovered `Widget.java`, does not remove unrelated compiler errors, and does not establish classfile byte identity, StackMapTable compatibility, original-game runtime behavior, or redistribution rights. The 14 method verifiers remain **individual** original Code proofs. The latest comparable complete-source compiler frontier remains 1,295 Java sources and 2,358 errors.

## Required next acceptance

Compile the ACTUAL unchanged complete `rs/interfaces/widgets/Class179.java` with the ACTUAL `Widget.java` and independently recovered readable dependencies where available, and only separately labeled compiler-only signatures for missing dependencies. Compare the single emitted class's 14 method Code attributes against the original source-evidenced mapping, clearly isolating R214 and R217 normalization. Record every source input SHA, temporary nonoriginal helper and exact compiler command. Do not promote the individual 4,314-operation claims into a whole-class source-compilation claim until that build succeeds.

PR stack: [R219 #1106](https://github.com/Trexzo/SpawnPK-Client/pull/1106) → R220; original client milestone [#1004](https://github.com/Trexzo/SpawnPK-Client/issues/1004).
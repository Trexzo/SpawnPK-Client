# Original SpawnPK v311 R134 — owner-private source-recovered `rs/secure/c`

**Owner-original source authority:** v311 client JAR SHA256 `5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`. This checkpoint is a **certified source-recovered JVM island**, not complete game-client runtime acceptance. The original game JAR, owner-private reconstructed Java source, compiled game binaries, original game assets and the private verifier/ZIP remain **OFF public GitHub**.

## R133 blocker resolved: EXACT original 334/334 JVM instruction parity

New distinct original-v311 JVM class identity **`rs/secure/c.class`**, original class SHA256 `62b8bf45ecbdcc3bfa6ef1899b11fe398076588b718aad9478af030a5b5f9a79`; R134 Java9-source rebuilt (after reviewed original metadata-only restoration) class SHA256 **`1b92993f80e4a480bab90238592cbe11a4528ca3c9928da9b61c8b9ed6bceed4`**.

**334/334 EXACT original ordered symbolic JVM instructions**, matching `javap -p -s -c` method/field declarations and descriptors, all byte offsets, operand references and original `try/catch/finally` exception-handler boundaries. Compiler source targets `javac --release 9 -g:none -proc:none` with **EMPTY compiler classpath and sourcepath**; one Java source emits exactly one original-named class, no original game/vendor binary compiler dependencies, no unreviewed game source stubs, no temporary donor classes.

R133's 338-instruction mismatch was fixed in actual **Java source** by removing two unnecessary intermediate return variables in nested resource/finally parsers. The Java9 compiler now generates the same original return, resource-close, suppression and finally bytecode: **334, not 338 instructions**.

The original parent method reference `rs/u/a.a:(Ljava/lang/String;)Z` is unavailable at Java source compilation time. A reviewed **copied-classfile CONSTANT-POOL metadata-only transform** restores exactly one compile-only `java/lang/Boolean.parseBoolean:(Ljava/lang/String;)Z` Methodref's owner and name to the exact original `rs/u/a.a:(Ljava/lang/String;)Z`. A reviewed declaration-metadata-only transformation removes **exactly four compiler-generated checked `Exceptions` attributes**. **All seven compiled executable `Code` attribute payloads (including handlers) remain byte-for-byte unchanged before/after metadata restoration**, enforced by independent SHA-256 checks. **No JVM executable `Code` byte is patched.** The original `rs/u/a` parent implementation itself is **NOT** recovered; full uncached source/runtime closure is **NOT** claimed.

### Crucial extra parity: StringConcatFactory bootstrap recipe

The compiler-visible `invokedynamic makeConcatWithConstants` instruction list can remain **identical** despite different embedded concatenation recipes that change runtime outputs. The original owner-v311 recipe is **`WINDOWS \\u0001\\u0001`**, not simply `\\u0001\\u0001`. R134 reconstructs that genuine constant in Java source and compares the original and rebuilt JVM **BootstrapMethods** method arguments via `javap -v`, separately from all 334/334 instruction checks.

The fail-closed negative suite specifically tests this: the candidate changes `WINDOWS ` to `OTHER ` in both expression sites, recompiles with identical visible JVM instruction count and opcodes, and repins **BOTH** candidate source and compiled class SHA values. **The verifier still rejects the wrong bootstrap recipe before any runtime test**. This closes a blind spot in the earlier R133 bytecode-only audit and prevents declaring equal `invokedynamic` semantics just from opcode displays.

### Safe bounded original/rebuilt runtime evidence

**38/38 original-JAR versus rebuilt Java9 source observations are identical**, with **NO original game JAR in the rebuilt runtime classpath**. The pinned probe compares:

- Reflection of public cache state, getter and private process/date-parser declaration shapes, including empty checked exception declarations.
- Eight wholly fictional nonnull cache seeds plus a synthetic null cache, setting cached-done flag `b=true` **BEFORE every getter call**.
- Six fixed fictional date strings parsed in deterministic UTC / English JVM settings, including intentionally invalid dates.
- In-memory fake `Process` objects with fixed synthetic input streams for private parser methods: valid install date, missing field, malformed field, two well-formed UTC strings, malformed UTC and empty content; checks each fake process's destroy count and resulting messages/exceptions.
- Both original and rebuilt processes avoid real `systeminfo`, PowerShell, external process launch, hardware fingerprinting, network requests, real host identifiers, actual original game/runtime and Windows installation-date retrieval.

**Important scope:** The real uncached outer `a()` entrypoint may launch system commands and requires the original `rs/u/a` method; this path was **NEVER executed**, and is not behaviorally certified despite full authentic JVM code/metadata parity. Original full classfile binary-byte identity and the original author's Java source text are not claimed.

### Private clean archive replay and 12 strong refusal cases

Private archive **`SpawnPK-v311-R134-Secure-C-1-Class-Private-Sources.zip`** SHA256 **`62d0230e0d0c1bce2f0c1696fc7727cea21e68073704dd2e954bce34f7604922`**, **11,920 bytes / seven ZIP entries**, contains only Java source, a fixed original SHA authority manifest, safe Java probe, source compiler metadata restorer, strict original verifier, negative tests and README. Contains **NO original JAR, compiled original/rebuilt game/vendor classes, game assets, hardware identifiers or credentials**. **The entire owner-private archive stays OFF public GitHub.**

An **independent FRESH archive extraction** was fully recompiled and replayed against the original pinned v311 JAR: exact one-class source output, rebuilt SHA pin, original **334/334** bytecode and handlers, authentic bootstrap recipe, **38/38** bounded original/compiled-safe observations, verified original SHA authority, and **12/12 fail-closed deliberate-invalid cases**:

- Tampered source, missing source, extra unreviewed game Java source, changed probe, altered restorer, modified verifier and README;
- Wrong original JAR pin, tampered original class SHA, fabricated increased distinct class ledger;
- **Real JVM condition branch mutation after BOTH candidate Java source and rebuilt class SHA values were repinned**, refused by original symbolic JVM instruction comparison;
- **Different runtime string-concat bootstrap recipe with identical visible `javap` instructions after BOTH candidate Java-source and compiled-class SHA values were repinned**, refused by original BootstrapMethods comparison.

The private ZIP and all owner-original sources, verifiers, manifest and game binaries are **not** uploaded to public GitHub. [Public wholly fictional Java9 resource-return and bootstrap regression](../tests/test_v311_synthetic_resource_return_bootstrap_island.py) has **2/2 independently locally passed** tests and contains no original project Java/binary/identifiers/actual serial retrieval code. Hosted public CI is separate, and does **not** execute private original-v311 parity verification.

### Recovery accounting / next dependency

R132/R133 certified distinct original recovery remained **133/1,184 original JVM class identities / 11,822 matching instructions**, across separate recovered source islands. R134 adds **ONE NEW class and 334 NEW original symbolic JVM instruction matches**, resulting in **134/1,184 distinct original classes / 12,156 exact original JVM instructions** across separately certified source builds. **The largest single integrated source-build group remains R129 99 original-named classfiles / 10,150 original instructions**, NOT a 134-class jointly compiled client.

Original `rs/secure/a`, `rs/secure/b` and now `rs/secure/c` are individually accepted authentic direct dependencies of the original `rs/u/a` owner, **but `rs/u/a` itself remains unrecovered**; other outstanding direct dependencies, exception behavior and original outer-class reflection must be addressed without fake game implementations. `rs/n/c/ap`, `rs/f/a`, scene `rs/a/a`, renderer `rs/k/e`, provisional tiles, whole client/native/GPU/gameplay also remain unaccepted. The R126 nested original enclosing-class/invalid enum valueOf non-parity remains unresolved.

**Keep [draft PR #1142](https://github.com/Trexzo/SpawnPK-Client/pull/1142) DRAFT and UNMERGED**. No manual gameplay, command, hardware identity or host OS test is required for this source-only milestone.

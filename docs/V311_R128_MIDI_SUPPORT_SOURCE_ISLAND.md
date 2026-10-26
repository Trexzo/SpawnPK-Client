# Original SpawnPK v311 R128 — privately recovered MIDI controller dependency

**Date: 2026-10-24.** Owner-provided exact v311 JAR SHA256: `5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`. Original client JAR, reconstructed owner-private Java and private verifier/ZIP remain **off public GitHub**.

## One genuinely NEW original v311 class

Original JVM identity **`rs/v/c.class`** is a standard-Java MIDI sequence, synthesizer and volume-control helper. Its original uncompressed classfile size is 4,222 bytes. Exact original owner class SHA256 **`2e4a92a71fb29cf8a7815bda8d245c49366416c4caca670a4453cc87d7499c0c`**; privately Java9 source-generated class SHA256 **`76b0602cc417f7d5ad4e21255d629016ac2ba9ad4b39fbe781b6d1097da02b80`**.

**261/261 ordered owner-original symbolic JVM instructions match** the separately compiled Java9 source class; `javap -p -s -c` declaration, symbolic operands, numeric byte offsets, method/field descriptors and the original MIDI-method exception handler boundaries all match, normalizing numeric constant-pool indices only. This is **not** a full bitwise original classfile identity or author-original Java-text claim.

The private `javac --release 9 -g:none -proc:none` build compiles **exactly one Java source** to the **one original-named `rs/v/c.class`** output with an **EMPTY javac classpath AND sourcepath**, zero original `rs/` game binary compiler dependencies, zero third-party vendor binary dependencies, zero implementation source stubs and no temporary donor classfiles.

### Exact bounded original-vs-rebuilt behavioral evidence

**37/37 original-owner-v311 vs source-rebuilt behavior/reflection observation lines match** from separate headless JVM runs, **without original game JAR on the rebuilt runtime classpath**. The R128 probe checks string accessors/mutators, initial and saved volume, volume changes with/without persisting settings, three dynamic-proxy MIDI channels, null channel arrays, 16-channel `ShortMessage` events to a fake `Receiver`, reflected field/method signatures and Java method modifiers. The probe uses **no physical MIDI hardware or network access**. It does **not** invoke MIDI playback/sequencer startup `d()`; exact 261/261 original JVM bytecode parity **includes** that method, but no real device/playback compatibility is claimed.

### Clean archive replay and fail-closed cases

The private source archive `SpawnPK-v311-R128-MIDI-1-Class-Private-Sources.zip` SHA256 **`a71ba2ed6aac4ae324fae03d90e700ff29903a537c3851420730ad8a79a7b363`**, **8,482 bytes / six source-manifest-probe-verifier entries**, was **independently clean extracted** and revalidated: original SHA/JAR/class pins, exact one-class output set, source-generated class SHA and **261/261 symbolic JVM instruction parity**, headless **37/37 behavior/reflection observations** with original-JAR-free rebuilt runtime.

**8/8 deliberate-invalid source/candidate checks REFUSED** from that fresh extraction: altered source, missing source, extra fake Java source stub, changed Java probe, artificially inflated recovered-class count, wrong original game JAR SHA, wrong original class SHA, and a **REAL changed getter JVM instruction** with BOTH mutated Java source SHA and recompiled output class SHA deliberately refreshed. The last candidate passes source/class hash preflight but is rejected by **`ORIGINAL_JVM_PARITY_MISMATCH`**. Private archive contains **no original client JAR, compiled game/vendor binaries, game assets or credentials** and must not be uploaded to public GitHub.

The [public independent synthetic-only Java9 MIDI source-island regression](../tests/test_v311_synthetic_midi_support_source_island.py) uses only fictional class and method names and data; locally **2/2 tests passed** (deterministic JDK9 build, simulated MIDI send behavior, and actual JVM instruction difference after refreshing Java source and compiled class SHA). This is a separate public safety check: **public hosted CI cannot attest private owner-original v311 bytecode parity**.

### Distinct accepted class accounting and remaining blockers

Previous R127 original-v311 cumulative: **129 distinct recovered class identities / 11,206 matching original JVM instructions across SEPARATE source islands**. R128 adds **one genuinely NEW `rs/v/c` original class identity / 261 NEW matching JVM instructions**. New cumulative **130/1,184 original classes / 11,467 original JVM instruction matches across separately verified source builds**. **Largest integrated ONE source compilation is unchanged: R127 98 original-named classfiles / 9,889 original instructions**. Do NOT call this a 130-class common compilation.

The original not-yet-recovered `rs/u/a` parent directly refers to `rs/v/c`: accepted direct project dependency coverage there improves by one. Other original `rs/u/a` dependencies remain unaccepted, so the original outer is **NOT source recovered**. Genuine `rs/n/c/ap`, `rs/f/a`, original scene `rs/a/a`, renderer `rs/k/e`, original whole client/native/GPU/gameplay remain unaccepted. Original R126 nested enum `getEnclosingClass()` and invalid `valueOf` reflection mismatches remain **UNRESOLVED** and are not addressed by the MIDI helper.

Keep [PR #1142](https://github.com/Trexzo/SpawnPK-Client/pull/1142) **DRAFT and UNMERGED**. No manual game testing at this source-only milestone.

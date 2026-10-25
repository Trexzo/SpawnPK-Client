# Original SpawnPK v311 — R129 certified private 99-class Java9 common source build

**Evidence date:** 2026-10-25. Owner original v311 client JAR SHA256 `5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`. Reconstructed original Java sources, owner original JAR, compiler/probe source archive and compiled game/vendor binaries are **NOT** committed to GitHub.

## Integration, not newly accepted distinct classes

R129 integrates the **PREVIOUSLY R128-ACCEPTED** original MIDI support class `rs/v/c.class` into the R127 source build: **one `javac --release 9` invocation of exactly 93 recovered owner-private Java source files** emits **99 selected original-named JVM classfiles / 10,150 previously verified original symbolic JVM instructions accounted for**. The prior biggest single source group was R127 **98 / 9,889**.

**ALL 98/98 prior R127 generated class SHA256 hashes are byte-for-byte unchanged.** The new integrated `rs/v/c.class` has the exact previously accepted R128 rebuilt SHA256 `76b0602cc417f7d5ad4e21255d629016ac2ba9ad4b39fbe781b6d1097da02b80`, and its original-vs-rebuilt `javap -p -s -c` field/method declarations, bytecode offsets, symbolic operands, method descriptors and ordered instructions match **261/261**. The genuinely original MIDI class fingerprint is `2e4a92a71fb29cf8a7815bda8d245c49366416c4caca670a4453cc87d7499c0c`.

The compilation selects exactly **99 original-named classfiles**, with **no** temporary donor owner outputs, unreviewed original-game implementation stubs or `rs/` game binary inputs on the compiler classpath. Binary compiler dependencies are exclusively authenticated genuine vendor-only GNU Trove, Google, LWJGL and javax.inject annotation classes extracted privately from the pinned original JAR; these binaries are **not distributed**. Earlier reviewed compile-only type/package aliases remain intact, with no new source alias needed for `rs/v/c`.

### Owner-private clean archive replay and mutation refusal

Archive: `SpawnPK-v311-R129-99-Class-Private-Integrated-Sources.zip`, SHA256 **`113344719da53fd58f90aab1e8054db92bdeb2872bbbbf0e45954592f1279f0b`**, **350,237 bytes / 193 entries**. It contains owner-private Java sources, SHA-pinned R127/R128 manifests, probes, compiler and verifier tools, and README; **NO original client JAR, compiled original/rebuilt game/vendor binaries, game assets or credentials**. This archive remains **OWNER-PRIVATE and is NOT uploaded to public GitHub**.

The final archive was independently **CLEAN-EXTRACTED** and passed full verification against the exact original client JAR: 99/99 selected original-named outputs, 98/98 unchanged prior class SHA fingerprints, 1/1 previously accepted MIDI compiled SHA, and 261/261 original MIDI symbolic JVM instruction parity. Eight bounded original-vs-rebuilt reflection and behavior probes match:

| Probe | Matching original observations | Original game JAR needed on rebuilt runtime classpath? |
| --- | --- | --- |
| R111 overlay | 65/65 (+ sentinel) | No |
| R120 scene callbacks | 20/20 | **Yes, trailing runtime-only fallback** |
| R114 UI enums | 20/20 | No |
| R117 scene node | 24/24 | No |
| R116 renderer mode | 17/17 | **Yes, trailing runtime-only fallback** |
| R123 environment enums | 53/53 | **Yes, trailing runtime-only fallback** |
| R126 nested magic enums | 63/63 functional cases | No |
| R128 MIDI controller | 37/37 | No |

A separate clean-extracted `negative_r129.py` suite passed **9/9 deliberate fail-closed refusals**, including source changes, missing/extra source, altered compiler/probe/verifier, false class counts, wrong original JAR, and a **REAL changed MIDI getter JVM algorithm after BOTH source SHA and built-class SHA were repinned, with the nested R128 manifest itself repinned**. Candidate SHA preflight passes; the strict **owner-original JVM instruction comparison** still rejects with `ORIGINAL_JVM_PARITY_MISMATCH rs/v/c.class`.

The [public independent synthetic-only Java9 regression](../tests/test_v311_synthetic_midi_common_build.py) uses invented unrelated class identifiers, a toy MIDI routine, and no recovered game source/data. Its two local tests passed; public hosted CI is a **separate safety check** and cannot certify private original-JAR comparison.

### Precise recovery ledger and limits

**Cumulative DISTINCT accepted owner-original v311 recovery remains 130 / 1,184 class identities and 11,467 matching original JVM instructions ACROSS separately certified private source groups**. R129 adds **ZERO new distinct identities or instructions**. Only largest **ONE** source-generated compilation grows R127 98/9,889 → **R129 99/10,150**. Never describe this as a one-shot 130-class source compile.

The genuine original outer owners `rs/u/a`, `rs/n/c/ap`, `rs/f/a`, original scene model `rs/a/a`, renderer `rs/k/e`, seven provisional tiles, whole-client source, real MIDI hardware playback, native/GPU graphics and gameplay acceptance remain **unverified**. In particular the R126 `getEnclosingClass()` and invalid enum `valueOf` reflection non-parity is **NOT fixed by this integration**. The rebuilt R128 MIDI probe uses a simulated receiver, not physical audio hardware.

Keep [draft PR #1142](https://github.com/Trexzo/SpawnPK-Client/pull/1142) **DRAFT AND UNMERGED**. No manual game test required for this bounded original-source integration milestone.

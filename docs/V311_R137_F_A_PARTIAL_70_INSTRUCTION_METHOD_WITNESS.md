# Original SpawnPK v311 — R137 PARTIAL rs/f/a METHOD WITNESS (not a recovered class)

**Checkpoint date:** 2026-10-25. **Status: six original-method source witnesses verified; ORIGINAL OUTER CLASS NOT RECOVERED.** Owner-v311 original binary SHA256 `5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`; authentic `rs/f/a.class` SHA256 `01f0546471ba05b71cf4ceb8245f76fde9c3306375db41ef21323c8885d0281e`.

This public report deliberately contains **NO reconstructed private game Java source, original game JAR, recovered compiler inputs, game/vendor classfiles, bytecode restorer, original program data, or device/account identifiers**. The full private research ZIP is deliberately retained OFF public GitHub.

## Original method-level reconstruction — EXACT 70/70, incomplete 1,348-instruction owner

A private JDK9-only **partial** source class with a convenient (NON-original) test-only static initializer, built under `javac --release 9 -g:none -proc:none` and EMPTY javac classpath/sourcepath, now contains six specific exact owner-original method JVM witnesses:

| Exact original method declaration | Matching original ordered symbolic JVM instructions |
| --- | ---: |
| `public rs.f.a();` | 3/3 |
| `public static boolean a();` | 2/2 |
| `public static boolean b();` | 2/2 |
| `public static boolean c();` | 2/2 |
| `public static void a(boolean);` | 20/20 |
| `public static void e();` | 41/41 |
| **Only these six methods** | **70/70** |

The original **whole `rs/f/a.class` contains exactly 1,348 JVM instructions**. Its other **1,278 JVM instructions**, original static initializer, settings serialization/deserialization, original complete field declarations, genuine outer runtime and game dependencies remain UNRECOVERED. The compiled partial source classfile **must not be installed or used as an original `rs/f/a` class**. This is a bounded **METHOD WITNESS, NOT an accepted distinct recovered JVM class**, even though these selected Code methods match exact original ordered opcodes, byte offsets, symbolic operands and method descriptor signatures.

The flag toggler `a(boolean)` writes the genuine original `rs/l/E.i:Z` static project field. The isolated Java9 compilation temporarily uses a local Boolean field and the private verifier retargets this particular field reference on a **COPIED classfile constant-pool metadata-only** transformation. ALL **seven** compiled Code attributes (six selected method Codes plus the **UNACCEPTED fake initializer**) remain byte-for-byte unchanged before/after the transform. It does NOT use an original game binary javac dependency or a fake game implementation source stub, and **neither original nor restored `a(boolean)` is called on the retargeted research output when `rs/l/E` is unavailable**. The unretargeted local test class may use its own fake temporary field to check branch semantics, without representing original game behavior.

**Safe bounded local-only test:** the partial output executes the two constant-false methods, one delegator and ten keycode entries, and its unretargeted local compiled variant executes the flag toggler using only its own Java static fields. **Ten local-only synthetic observations** passed; **the real owner-original `rs/f/a` class was NEVER initialized or executed**. No original-vs-rebuilt game runtime behavior parity is asserted for this partial outer.

## Exact owner-v311 dependency graph and circular blocker

A private `javap -v` original constant-pool direct **Class** reference audit with two SHA-pinned owner-original `rs/f/a` and `rs/u/a` classfiles demonstrates:

- Original `rs/f/a` references **ten OTHER original game project JVM class identities**, excluding itself.
- **Six are already recovered and present in previous certified source islands**: `rs/f/a$a`, `rs/f/a$b`, `rs/f/a$c`, `rs/f/a$d`, `rs/h/c`, `rs/n/c/ap$a`.
- **Four are NOT original-source recovered**: `rs/V`, `rs/l/E`, `rs/n/c/ap`, `rs/u/a`.
- There is a real **DIRECT circular original game dependency `rs/f/a` ↔ `rs/u/a`**; the genuine original `rs/u/a` remains missing and in turn has `rs/f/a` as its one missing direct other original project class among seven.

These are exact **direct JVM constant-pool references**, NOT a complete call graph, transitive source closure, or runnable client certification.

## Clean private ZIP replay, strict negative checks

Private owner ZIP `SpawnPK-v311-R137-F-A-Partial-70-Instruction-Private-Research.zip`, **12,175 bytes / 8 entries**, SHA256 **`36f351a51795be6a9c1bca7d68fa983987b8db2173372864575f861b2d2b0f8a`**, contains ONLY one incomplete private Java source, pinned original-JAR/class and compiler hashes in a research manifest, safe local Java test, private constant-pool metadata-only restorer, method verifier, negative tests, direct dependency audit and README. **NO original game JAR, compiled original/rebuilt game/vendor classfiles, game assets, actual user/device identifier, credentials or account material**. Private ZIP and entire owner-private research source **are kept OFF public GitHub**.

Independently CLEAN EXTRACTED archive replay passed **all six method comparisons 70/70**, all seven Code payloads remain unchanged by metadata-only transformer, **10 local-only safe observations**, unchanged recovery ledger and explicit non-acceptance of the full outer, and exact project dependency audit with reciprocal original outer references.

**12/12 deliberate-invalid candidates refused**, including changed/missing/unreviewed source, altered verifier/restorer, forged original class SHA, false 135-class credit, a false completed-parent declaration, false cumulative instruction ledger, and **TWO fully repinned real modifications**: changed actual JVM keycode constant after recomputing BOTH Java-source SHA and compiled candidate-class SHA; changed *symbolic JVM owner* `rs/l/E` to a wrong type after updating restorer/source-generated class pins. Both reach original method symbolic JVM comparison and fail there, NOT merely the superficial hash preflight.

The [PUBLIC synthetic-only Java9 partial-method witness regression](../tests/test_v311_synthetic_partial_method_witness.py) uses only toy classes and fictional values; its **2/2 local tests passed**. Public hosted CI is independent of these owner-original private comparisons.

## Accurate unchanged accepted ledger / next milestone

**R137 adds NO newly accepted original-v311 class and NO instruction credits to the accepted cumulative ledger.** Authentic **DISTINCT accepted original-v311 recovery stays 134/1,184 class identities and 12,156 original JVM instruction matches ACROSS separately accepted source islands**. Largest **ONE common Java9 compilation remains R136 with 106 original-named classfile outputs / 10,960 original JVM instructions**. The 70 matching R137 partial method instructions **are NOT added**.

Next: recover the remaining genuine `rs/f/a` initializer, file settings methods, and missing direct project owners `rs/V`, `rs/l/E`, `rs/n/c/ap`, and resolve the mutual `rs/f/a` / `rs/u/a` dependency without fake game class implementations. Exact original fields, all 1,348 instructions, exception tables, `BootstrapMethods` recipes, source-only compile, privacy-safe behavior probes and fully repinned mutation refusals remain required before acceptance. Original `rs/u/a`, game GUI, renderers, full game runtime/native GPU/gameplay still NOT certified.

Keep [PR #1142](https://github.com/Trexzo/SpawnPK-Client/pull/1142) **DRAFT and UNMERGED**. No manual gameplay or machine-identification commands requested for this partial method research.

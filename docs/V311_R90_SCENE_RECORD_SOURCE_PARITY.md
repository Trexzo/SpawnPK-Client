# Original SpawnPK v311 R90 — private 61-class scene color and text records

**Verification date:** 2026-10-23. Owner-provided original client JAR is pinned by SHA-256 `5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`. The original JAR, reconstructed original-game Java, compiled game classfiles, private probes and private ZIP are **not committed to public GitHub**.

## Two newly reconstructed original Java9 classes

| Original JVM class | Exact original class SHA-256 | Independent source-built class SHA-256 | Original ordered JVM instructions |
| --- | --- | --- | ---: |
| `rs/l/e/j.class` — polygon-backed selectable color record | `d379e3f3a61a82b678fd6edf16feb3294ebfce44838295501c09fe36b366bcc8` | `47d97808b99dabd204af484735f54b461e7ff8f330bd8c24380ead3705a2caa7` | **54/54** |
| `rs/l/e/b.class` — package-private text/timestamp fallback record | `6ba5d2d7141f0dc99ff3431ecbc9fe951cd6a6ce6412a266c2f77398cc994dbe` | `114b9ea4e1d6aad833def44db9a67ae6856c6866ee8e2602b3119182aca4218c` | **18/18** |
| **Newly accepted** | | | **2 classes / 72 original JVM instruction matches** |

Original declaration/descriptor shapes, ordered JVM opcodes, exact byte offsets/branch locations and resolved symbolic operands match independently compiled private Java source after normalizing **only numeric constant-pool indexes**. Both classes have zero project-class dependencies outside themselves, and the original `rs/a/a` scene-model class directly references `rs/l/e/j`. Resolving this scene-data leaf does **not** resolve the remaining `rs/a/a` source dependency graph.

## No-stub source build and bounded actual behavior

The prior accepted R88 **59 reconstructed original Java files** plus the two new Java files compile **in one** `javac --release 9 -proc:none -g:none` source-only invocation with an empty original-game binary classpath and external sourcepath. The previously reviewed disposable compile-only `rs/k/c` class/package alias is inverse-restored in copied compiled classfile JVM names. All 59 previous original-name compiled class SHA-256 fingerprints remain **byte-for-byte unchanged**. Exactly 61 source-backed classfile outputs, **zero declaration-only source stubs**, and **zero missing explicit original project-class references** under SHA-pinned constant-pool/descriptor static dependency checks.

The closed source build accounts for **6,280/6,280 original JVM instructions**: all previous R88 6,208 original instruction matches are certified by their unchanged private compiler class hashes, and the new 72 were freshly original-versus-source-disassembled. This does **not** claim the earlier 59 classfiles were freshly re-disassembled.

A private JDK-only probe was compiled against the independently source-built classes (the original client JAR contains a conflicting `rs.l.e` class/package name), and then run against **separate original-JAR and rebuilt-class JVM classpaths**. It matched **92/92** deterministic behavior cases across polygon identities, normal/selected foregrounds, default translucent overlay colors, public color field mutation, null and Unicode text fallbacks, overrides and extreme timestamps. The earlier R88 behavior tests were **not rerun**. This does not claim native GUI rendering or full client gameplay acceptance.

## Independent clean extraction and refusal evidence

Owner-private ZIP: `SpawnPK-v311-R90-Scene-Records-61-Class-Private-Sources.zip` SHA-256 **`6868ba2065a757aa41e31fc5c562619447c03eaca38815a5f5c1f9ddb1716a5c`**. Contains exactly 61 reconstructed owner-private Java source files, original/source/rebuilt SHA manifests, private deterministic behavior probe, independent source verifier and refusal tests. **No original game JAR, compiled original game classfiles, game assets, font binaries, credentials or tokens.**

After **fresh extraction** the verifier passed the complete 61-source Java9 compilation, 59 previous fingerprint-preservation checks, both new symbolic original JVM comparisons and all 92 behavior cases. **Five/five clean-extracted deliberately invalid cases** failed closed: tampered source SHA; deleted original-name Java source; wrong original JAR SHA; unreviewed temporary alias; changed actual original JVM instructions after **repinning both candidate source and rebuilt-class SHA fingerprints**. These last negative cases were run separately in bounded executions, not inferred from static SHA equality.

## Distinct cumulative accounting and exclusions

Previous R88 accepted cumulative: **88 distinct original-v311 source-recovered classes / 7,416 exact original JVM instruction matches** across separately certified source builds. New **2/72** yields **90 distinct accepted original classes / 7,488 cumulative original JVM instruction matches** across separate source-build records.

The largest single, fully static-dependency-closed original-source compilation is **61 classes / 6,280 instructions**, **not a 90-class single compilation**. The seven earlier tile sources including `rs/I` remain provisional because large original `rs/k/e` renderer and `rs/a/a` model dependencies are still unrecovered; `rs/l/e/k` is among the unresolved model dependencies and uses third-party GNU Trove types not included in this isolated no-game-binary compiler classpath.

[Unrelated synthetic-only Java9 source-island regression](../tests/test_v311_synthetic_scene_color_record_source_parity.py) exercises original-vs-independent-toy-source bytecode parity, headless color/text behaviors and fail-closed mutations, without original game code or the private JAR.

Keep [PR #1142](https://github.com/Trexzo/SpawnPK-Client/pull/1142) **DRAFT and UNMERGED**. Full original 1,184-class source recovery, exact original binary/classfile attribute equality, reflection/native/asset closure, OpenGL and live-client/gameplay acceptance remain **unproven**.

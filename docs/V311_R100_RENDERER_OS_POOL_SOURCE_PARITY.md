# Original v311 R100 — OS detection enum and 6,048-entry renderer pool source parity

**Owner-private verification date:** 2026-10-23. Exact original v311 owner-supplied client JAR SHA256 `5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`. The original JAR, reconstructed game Java, compiled original-name game classfiles and real GNU Trove vendor binary classes are **NOT published to GitHub**.

## Two newly accepted original-v311 Java9 classes

| Original JVM class | Original class SHA-256 | Independently compiled, inverse-restored class SHA-256 | Matching original ordered JVM instructions |
| --- | --- | --- | ---: |
| `rs/k/j.class` — OS-detection enum | `820acef9584e669760389461af78b899530a32ef1dfcd5b4c22a72b3309d995e` | `fdf939968a7df62560803b4f01c78dcc372228d07a5ffb3bb684139b7bc5bcdf` | **94/94** |
| `rs/k/b/g.class` — pooled renderer record, Trove-backed registry | `89b3c4496bb000a9d6cc5fe3bb70006e6cbd8c1c82bbc5331eafca29d9b565fc` | `24596bcaf2fbd3902f8b2c9491c9f756d73a318e452731636753e5deb4d053c1` | **73/73** |
| **New accepted** | | | **2 genuine original classes / 167 instructions** |

These two actual source files are newly recovered: they did **not** appear in the previously accepted 70 R98 original-classfile output or in the earlier distinct-class ledger. Both reproduce original class/member declarations and descriptors, ordered JVM opcodes, byte offsets, branches and symbolic operands, normalizing only numeric constant-pool indexes. Original `javap -p -constants` output also matches rebuilt declarations. No original complete-classfile-byte identity, original authored source text or StackMapTable/attribute equivalence is claimed.

The `rs/k/j` enum preserves original runtime `Enum.name()` values `Windows`, `MacOS`, `Linux`, `Other`, while a narrowly reviewed copied-JVM-metadata transform restores compiler-generated/obfuscated field names `a/b/c/d`, the static detected `e`, generated array `f` and helper method `b()`. Its `os.name` Java system-property branches preserve original instruction offsets for `mac`, `darwin`, `win` and `nux` detection.

The `rs/k/b/g` record reconstructs a **6,048-entry original Java static pooled-object array**, three integer field getters/setters, a cursor-reset operation and genuine obfuscated `gnu/trove/f/b/cc` int-to-object map operations. Its original JVM Trove references are inverse-restored after compiling against a **real, original-derived vendor-only binary classpath**, not a mocked or stubbed map.

## Exact 72-classfile original-source-generated build and bounded behavior

The previous R98 build contained **69 reconstructed original Java source type declarations + one original synthetic switch-table donor source**; javac emitted 71 temporary classfiles, discarded the donor owner and restored 70 original JVM class identities. R100 adds **two genuine original Java source classes**, giving **71 original Java type source declarations + one switch-map donor source**. One `javac --release 9 -proc:none -g:none` invocation now emits 73 temporary classfiles, discards the donor owner and inverse-restores **72 original-named Java9 classfiles with 7,189/7,189 accounted-for original symbolic JVM instruction matches**.

**All 70/70 previous R98 compiled-class SHA-256 fingerprints are unchanged**, including the previously recovered synthetic switch table, so its 7,022 original instructions retain their R98 source-parity certification. The two new 167 original JVM instructions and full declarations were freshly original-versus-rebuilt `javap -c -p -s` compared. The source build has **zero temporary source stubs and zero missing explicit original `rs/` project-class dependencies** under the original constant-pool/descriptor scanner.

A SHA-pinned GNU Trove **vendor-only binary compiler dependency** is extracted at verification time from the exact original owner-provided JAR: **1,595 `gnu/trove/` original third-party vendor classfiles; ZERO original `rs/` client classfiles**. The existing reviewed reversible original `rs/k/c`, `rs/k/a` class/package and seven Trove nested-class aliases remain temporary, with original JVM identities restored on copied output. Real vendor binaries and original game binaries are not shipped or committed. This is explicitly **not** a zero-binary compiler classpath, but does exclude original game classfiles and fabricated dependency stubs.

New deterministic original-vs-rebuilt JVM probes matched **126/126 cases** across six `-Dos.name` variations (`Windows 11`, `MacOS Sonoma`, `Darwin 24`, `Linux nux 6`, `generic`, `Win10`). These cover all four OS-enum detection branches, all original enum names/ordinals/reflection field identities, valueOf, values-array cloning, 11 extreme signed-map lookup and registry cases, pooled record setter/getter and identity behavior, cursor reset and map clear. The **older R98 behavior cases were not rerun** in this bounded R100 replay.

## Independent clean archive and seven negative trials

Owner-private source/verifier archive: `SpawnPK-v311-R100-Renderer-OS-Pool-72-Class-Private-Sources.zip`, SHA256 **`0aac3e3bd728f1b0616a7056d06ecaaa015e8a3f320ca13d00b5c0246eab7209`**, 121,311 bytes, **96 entries including exactly 72 Java sources**. No original client JAR, original/compiled game classfile, vendor classfiles, fonts, login tokens, assets or accounts are included.

After **fresh clean extraction**, the R100 private verifier independently compiled all 72 original-name outputs against the exact owner-held original JAR's real-vendor-only binaries, checked complete source/original/rebuilt SHA pins, original static project closure, 70 old rebuilt class SHA fingerprints, **167 new JVM instructions**, and **126/126 new behavioral comparisons**. All **seven deliberately incorrect scenarios passed as refusals from that clean extraction**:

1. Changed original Java source rejected on its SHA pin.
2. Missing original source rejected.
3. Wrong whole-original-JAR SHA rejected.
4. Wrong real original-vendor-class SHA rejected.
5. Unreviewed compile-only alias rejected.
6. Modified enum-member restorer code rejected.
7. Changed actual pooled-record JVM instructions rejected **even after repinning BOTH reconstructed source and rebuilt-class SHA-256 fingerprints**.

## Cumulative count, public tests and remaining blockers

Prior certified R98 cumulative: **98 distinct original-v311 recovered classes / 8,218 matching original JVM instructions** across separately accepted source builds. Two new original classes / 167 original instructions yield **R100: 100 distinct original v311 classes / 8,385 original JVM instruction matches cumulatively**. The **largest single dependency-closed source-generated output is 72 original-named classfiles / 7,189 instructions, NOT a simultaneous 100-class compilation**.

The [independently authored synthetic Java9 OS-detection and bounded-pool parity regression](../tests/test_v311_synthetic_os_enum_pool_source_parity.py) uses only toy source classes, tests multiple system properties and exact instruction mismatch refusal, and contains **NO original game Java source or client/vendor classfiles**. Hosted CI must be separately checked; it cannot repeat owner-private exact original-client proofs.

The larger `rs/k/e` renderer (previously reported with 36 direct project dependencies) and `rs/a/a` scene model remain unrecovered. The seven earlier provisional `rs/I` and tile sources remain unaccepted. Original complete classfile bytes/metadata, renderer/OpenGL implementation, native/dynamic/asset dependencies, authenticated game client, live game behavior and 1,184-class project-wide compilability are **not established**. Keep [PR #1142](https://github.com/Trexzo/SpawnPK-Client/pull/1142) **DRAFT and UNMERGED**.

# Original v311 R106 — exact color utility source recovery and rejected image-filter candidate

**Owner-private authority:** 2026-10-23, original `client(20261021-111920).jar`, SHA-256 `5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`. The original game JAR, authentic recovered game Java source, original-name compiled classfiles, real original/vendor binaries and private runtime probes are **not committed to this public repository**.

## One new and genuinely distinct accepted original source

| Original class | Original SHA-256 | Private Java9 rebuilt SHA-256 | Exact ordered original JVM instructions |
| --- | --- | --- | ---: |
| `rs/l/L.class` — RGB/HSL color and hue-blending utility | `6dfaab35a6a59f8af7d1efd41733c81ca951e71705f1ba29dbc40849237382d8` | `a105ea5e4326130cc180142e8b531d1a86af725268ddb351fc8f44290d5a5474` | **341/341** |

The independently authored Java9 source for the original class reproduces original class/member declarations and JVM descriptors, ordered instruction opcodes, **exact original instruction offsets, branch/switch destinations, symbolic operands, six-way tableswitch and numeric field ConstantValue**, normalizing only constant-pool numeric indexes. The original source identity, complete classfile bytes/StackMapTable attributes and live graphics output are **not** proven.

The new original class has **zero missing explicit project-class dependencies** and was not present in the 105-class accepted original source ledger or earlier source-island builds. Its JDK-only original-JAR-versus-source-built behavior probe passes **2,524/2,524 comparisons** across integer boundaries, 19 example signed and ARGB colors, eleven hues/shifts and ten weighted color blending percentages, with constant field/constructor reflection checks. Prior R105 behavioral cases were not rerun as part of this bounded R106 test.

## One compiled 78-class source island and privacy boundary

The new Java source compiles with all **77 R105 reconstructed original Java source files** in one `javac --release 9 -proc:none -g:none` build yielding **78 original-named classfile outputs / 8,325/8,325 accounted-for original matching JVM instructions**. Every one of the **77/77 previous R105 rebuilt classfile SHA-256 fingerprints remains unchanged**. Thus **7,984 prior original instruction matches are retained via unchanged compiled hashes**, while **341 new original JVM instructions were freshly original-versus-rebuilt compared**. There are **zero declaration-only source stubs and zero missing explicit original project-class dependencies**.

As in R105, authentic third-party vendor-only binary dependencies (1,595 GNU Trove, 2,607 Google, 967 LWJGL classes) are extracted at replay time **only from the exact SHA-pinned owner original JAR**, with **zero original `rs/` game binary classfiles** on the compiler classpath. Earlier source/class/package and vendor-only compile aliases and metadata restorers are retained. The original game JAR and private compiled/vendor binaries are NOT distributed or publicly hosted. This build is **not** a zero-binary-classpath build; it is an original-*game*-binary-free compilation using verified external vendor library binaries.

## Rejected candidate — explicit negative source-parity evidence

The adjacent `rs/l/G.class` (AWT RGB image filter) was also independently investigated but **NOT ACCEPTED**. Its genuine original JVM constructor stores a field before invoking its `RGBImageFilter` superclass constructor. A direct Java9 source implementation instead emits the mandatory superclass constructor invocation before the field store. Because the **original instruction order differs**, it is **excluded** from the accepted source/classfile and behavior ledger even if color values could agree. No implementation source stubs, disguised bytecode equivalence or fabricated count inflation were used to accept it.

## Full private clean replay and refusal checks

Private owner-only self-verifying ZIP: `SpawnPK-v311-R106-Color-78-Class-Private-Sources.zip`, SHA-256 **`7c2b1aff0e0f7ece5fcb7eecc39c7c2e8c7748519abcac5bf16487d84bc4ccda`**, 233,764 bytes, 137 archive entries, exactly **78 reconstructed source Java files**. No original game JAR, `.class`, `.jar`, third-party binary, game asset, credentials, token or font bytes appear in this ZIP.

A completely **fresh ZIP extraction** passed full original whole-JAR/SHA/source compiler/real vendor verification, exactly 78 compiled class outputs, **77 old rebuilt SHA hashes unchanged**, 341 newly compared original symbolic JVM instructions and **2,524 new original-versus-rebuilt behaviors**. It also passed **9/9 intentionally invalid refusal cases** from that clean extraction:

1. Modified candidate Java rejected on source SHA.
2. Deleted candidate source rejected.
3. Wrong whole-original-JAR SHA rejected.
4. Tampered authentic vendor-class SHA rejected.
5. Unreviewed compile-only alias rejected.
6. Modified Java compiler script rejected.
7. Modified prior JVM bridge metadata-restoration script rejected.
8. Modified new runtime behavior probe rejected.
9. Modified color arithmetic method rejected **even after updating both candidate source and compiled-class SHA pins**, because the authentic original JVM instruction comparison still detects the changed code.

## Audited count and scope

Previous accepted R105 **105 distinct original-v311 classes / 9,180 original JVM instruction matches across separately certified source builds** + genuinely new R106 **one class / 341 instructions** = **106 distinct original classes / 9,521 exact matching original JVM instructions cumulatively**. Largest **one-shot original-name source-generated class set is 78 / 8,325 instructions**, **NOT** a single 106-source-class compile.

[Public unrelated synthetic-only Java9 color/source-parity and refusal regression](../tests/test_v311_synthetic_color_transform_source_parity.py) exercises only freshly invented JDK-only toy classes and contains no original game source. Hosted GitHub CI cannot repeat exact private game-JAR comparisons, and must be checked independently.

The original larger `rs/k/e` renderer, `rs/a/a` scene model, large OpenCL-dependent `rs/k/k` and seven earlier provisional scene/tile classes remain unrecovered. No complete 1,184-class original source build, full original classfile binary identity, native/OpenGL runtime, live login or gameplay verification is claimed.

**Keep [PR #1142](https://github.com/Trexzo/SpawnPK-Client/pull/1142) DRAFT, UNMERGED.**

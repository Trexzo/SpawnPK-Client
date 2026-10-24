# Official SpawnPK v311 — shadowed label and Swing painter source parity

**22 October 2026.** Original binary is the user-uploaded private `client(20261021-111920).jar`, full SHA-256 `5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`. This report publishes only hash/count evidence. The original client JAR, reconstructed private Java sources, generated classfiles and local original-client harness are **not included in the public GitHub repository**.

## Independently reconstructed original classes

Two original-client Java 9 Swing classes were reconstructed from the user's v311 bytecode and compiled **together** with `javac --release 9 -g:none -proc:none -encoding UTF-8`. The compilation used **no original game/client binary on the classpath**.

| Exact original JVM class path | Original SHA-256 | Reconstructed Java 9 class SHA-256 | Verified ordered JVM instructions |
|---|---|---|---:|
| `rs/ui/components/shadowlabel/a.class` — JLabel implementation | `9d192675e8ac247f224483dcf3e85f9214ef4dc72713ba0cd567fbe4bd5f4797` | `6f704c189e427a33bc84913eb31e15191c22e7679c9b8653e5b5de978ae403c0` | **57/57** |
| `rs/ui/components/shadowlabel/JShadowedLabelUI.class` — Swing painter | `bc8997f2e1d0a3b60ab85d8391593a159da2f699ae2cc6b9bb37854aff5da6b4` | `68d3645c7f785ca92a889351534ec6e5fb0024cf4a867e1eda46f7e2dd051f96` | **36/36** |
| **Total** | | | **93/93** |

The classes have explicit **mutual type references**: the label installs the custom UI painter, and the painter tests/casts the label type, reads its shadow color and point offset, paints the shadow then foreground text. Both types are present in the source build; there is no unselected original project-class reference in this connected pair.

Original-versus-rebuilt `javap -c -p -s` declaration and descriptor lists matched, as did every JVM **byte offset, opcode, branch target and resolved symbolic operand**, normalizing only numeric constant-pool slots. This is stronger than successful source compilation but **not** the claim of byte-identical full classfiles; the actual compiled class hashes differ from the original. Complete metadata, original author syntax, resource dependencies and every runtime state remain outside the proof.

## Original-vs-rebuilt headless raster comparison

A separate local **JDK headless Swing** probe loaded original and recompiled classes from two isolated `URLClassLoader` instances, set the same text, font, foreground, shadow tint, shadow offset, enabled state and opacity, then rendered each `JLabel` to a **220×54 ARGB** `BufferedImage`. SHA-256 covers *every* ARGB pixel, row-major, including transparent pixels. The same six bounded scenarios produced equal hashes:

| Case | Original **and** recompiled ARGB SHA-256 |
|---|---|
| Plain shadowed text | `43b91a0a6ffc1e41fd86d9228c0812cb146f2182b081db3d0111a92bbc384a34` |
| Offset +2,+2 | `e732c11b85125feca8bfdd1e569a03ff8d44febfd32f2a26d51654b0266c9d8a` |
| Empty text | `61cd95df21c5126497e12a07d7031eaf7c2a2d0e1b2e4b25c290279609cd6501` |
| Negative X / positive Y shadow offset | `04e57cc3005fbf26a372727bdac9c791e8ccdfb4f9b37a731686d535ae250404` |
| Disabled label | `ac32cff155e3e4f07520db5ca444e0a73c56fd1919f3c1ae71a70003362a598e` |
| Opaque background | `b0ebf097933f85a7d242846aed550442e507ff90d30f613f4f0164b639938a45` |

This establishes **6/6 bounded exact headless pixel comparisons on the local JDK**, not GPU/Minecraft rendering, cross-platform font raster identity, authenticated gameplay, arbitrary strings/fonts or all Swing look-and-feel variants.

## Public regression and overall scope

`tests/test_v311_shadow_label_source_parity.py` independently compiles **two deliberately synthetic JDK-only** caption/painter Java 9 source classes, verifies pinned original-vs-rebuilt symbolic JVM parity and complete two-class dependency closure, compares six headless pixel cases, and requires modified shadow offset source to be **rejected**. The synthetic fixtures are *not* the reconstructed proprietary v311 Java sources; GitHub-hosted CI cannot replay the actual private original JAR.

The two original classes bring the attested aggregate to **47 distinct original-v311 Java source-rebuilt classes, 2,223 matching original JVM instructions across separate source builds**, adding 2/93 to the previously documented 45/2,130. **No 47-class single javac build** or full original v311 client recovery is asserted. Original `rs/V` scene/rendering, gameplay integration, complete binary classfile parity and other source dependencies remain unfinished.

Canonical privately reconstructed Java source and its SHA-pinned acceptance JSON were furnished separately as a private user-facing ZIP; nothing proprietary was committed to this public repository.

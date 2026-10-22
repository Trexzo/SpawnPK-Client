# Original v311 — three more independently rebuilt UI components

**Evidence date: 2026-10-22.** This document records actual private-original-client Java source reconstruction and headless JDK comparisons. It does not contain or release the original game's JAR, reconstructed Java sources, compiled game classfiles, client assets or any game server credentials.

## Original binary and compilation authority

Authoritative original `client(20261021-111920).jar` SHA-256:
`5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`.

Three *additional* original `rs/ui/components/` Java classes were independently reconstructed privately and compiled **together in one** `javac --release 9 -proc:none -g:none -encoding UTF-8` process using explicitly empty external compilation classpath and sourcepath. All resulting classfiles have major version 53 (Java 9), with **no original client/game binaries on the compilation classpath**.

| Original class | Actual original SHA-256 | Private independent rebuild SHA-256 | Exact ordered JVM instruction matches |
|---|---|---|---:|
| `rs/ui/components/y.class` (progress strip / percentage) | `384c90f1867804743d059f9cd0c5b878011e82d278f0dd45751800d6185fca93` | `ba3fbdf2911a398a4cd02b3bdc146955b8367a5a1c0afa47593a65e5f197e206` | **119/119** |
| `rs/ui/components/b.class` (tinted transparent button) | `28097fb666243aae95eacad2aef45c19198bfe63f9b70978770d1045eeb472f5` | `f22aa781f5374b871d96d5df115066d025f011fd8a3cc43aece8776ae64d2ce4` | **113/113** |
| `rs/ui/components/r.class` (mouse-event relay) | `71dbf912634da6f3b46d661f0d177657fabb83aeb429fdbba6a6f3db6eec5a8f` | `0759b3dcc71fff18cbb922211c44b045c2d72e6f39191c6d94c12d8951632916` | **34/34** |
| **Added together** | | | **266/266** |

Original and independent-rebuilt `javap -c -p -s` declarations, descriptors, **every original JVM opcode, exact instruction offset, branch target and resolved symbolic operand** match for all three. Only numeric constant-pool indexes were normalized. Original and rebuilt `javap -p -constants` also match, including the button's two `private static final int` values **120** and **10**. No JVM bytecode is reproduced in this document.

Private output class-path + SHA-256 manifest is `c937ee35fbb5b6cefa8e988791a0cad71d2a2ac44988cb7ca280134fdd54d5c6` (sorted `path + NUL + rebuilt-class-SHA + newline`).

## Actual original versus source-rebuilt headless UI behavior

**Progress strip (`rs/ui/components/y`):** For six `(max,value)` pairs `(100,0)`, `(100,30)`, `(100,100)`, `(100,150)`, `(1,-1)`, and `(250,35)`, separately loaded exact-original and rebuilt classes returned the same integer max/value, percentage, **and full 64×12 ARGB pixel SHA-256** after rendering to `BufferedImage`. This covers empty, partial, full, over-capacity and negative progress as bounded cases, not exhaustive behavior.

**Tinted button (`rs/ui/components/b`):** Five opaque/semitransparent color cases independently matched exact 60×24 pixel SHA-256, stored background tint, computed foreground, and `isContentAreaFilled()` state between original and rebuilt `JButton` subclasses in the same headless JVM. These cases include bright and dark backgrounds, varied transparency, and checkerboard drawing.

**Mouse relay (`rs/ui/components/r`):** An original-vs-rebuilt JDK test created two `JPanel` components in a shared parent and attached a capture listener to the target. Both adapters converted and dispatched left-button **pressed, dragged and released** events to identical target-relative coordinates `(-38,-6)`, and ignored the three corresponding right-button events. Exact captured original and rebuilt transcript:
`501,-38,-6,1,true;506,-38,-6,1,true;502,-38,-6,1,true;`

Total headless test proof: **11/11 full-raster cases** (six progress + five button) and **one six-input mouse sequence comparison** passed. The combined 11-raster original transcript SHA-256 is
`dd60a2b1b5c032adc4ac9d52a5726364d5c6d8ff3354c3b0e0f797f3b414fb44`.

These are *actual* original-JAR/JDK-only comparisons with privately reconstructed Java, **not** the game's graphical UI, GPU rendering, login, gameplay, or an authenticated SpawnPK server.

## Accumulated source recovery and strict limits

The previously certified [42 distinct original v311 classes](V311_UI_COLOR_TEXT_RENDERER_SOURCE_PARITY.md) had 1,864 matching ordered original JVM instructions, across separate source builds. Adding three unique verified classes with 266 original instructions gives **45 distinct source-recompiled original classes and 2,130 matching original JVM instructions**, aggregated across **separate** verified build records. All three classes added here were compiled as one private source build; **no single 45-class javac build was attempted or is claimed**.

Original and recompiled `.class` SHA hashes are **different**. Ordered symbolic instruction, method signature, compile-time constant and selected behavior matches are **not** full original classfile attribute/StackMapTable binary identity, dynamic resource/reflective dependency closure, complete game source reconstruction, v309→v311 lineage equality, or live GUI acceptance.

## Public regression without proprietary source

`tests/test_v311_ui_progress_button_mouse_parity.py` uses deliberately unrelated **synthetic JDK-only Java9** progress-strip, tint-swatch and pointer-relay classes. It independently compiles all three, uses the existing exact SHA-pinned `standalone_source_parity.py` verifier to recompile from source with no game binary fallback, and runs a headless original-vs-rebuilt pixel/mouse-forwarding comparison. An altered synthetic tint fails symbolic JVM parity and cannot generate a successful verification report. Hosted CI never runs the actual v311 original client or reconstructed proprietary source.

**Next source targets:** move from JDK-only UI components into connected UI/scene support classes with verified original `rs/` dependency closure, especially components calling recovered `rs/ui/components/d`, `w`, `a`, `x`, and the separately identified `rs/J` scene record. A later full-client build will still require the verified namespace legalizer and many more class implementations.

# Original v311 shadowed-label UI source: connected two-class recovery

**Evidence date: 2026-10-22.** All authentic original game-client Java recovery was performed privately from the user-uploaded original v311 JAR, SHA-256
`5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`.
Only this hash/measurement report and unrelated synthetic-JDK regression source are published to GitHub, **not** original Java source, game binaries, artwork, compiled client classfiles or private probe scripts.

## Actual mutual-dependency source recovery

Two original v311 Java classes were reconstructed privately and independently compiled **together in one Java9-target `javac --release 9 -proc:none -g:none` process** using empty original-game binary classpath and sourcepath. This is a real JDK/Swing connected pair with **two explicit original project dependency edges**:

- `rs/ui/components/shadowlabel/a.class` extends `javax.swing.JLabel` and installs `JShadowedLabelUI` in its constructors;
- `rs/ui/components/shadowlabel/JShadowedLabelUI.class` extends JDK `BasicLabelUI`, checks/casts instances of the original `a` label type, and draws text using its shadow color/point offset.

| Original v311 class | Exact original class SHA-256 | Independently compiled Java class SHA-256 | Matching original JVM instructions |
|---|---|---|---:|
| `rs/ui/components/shadowlabel/a.class` | `9d192675e8ac247f224483dcf3e85f9214ef4dc72713ba0cd567fbe4bd5f4797` | `6f704c189e427a33bc84913eb31e15191c22e7679c9b8653e5b5de978ae403c0` | **57/57** |
| `rs/ui/components/shadowlabel/JShadowedLabelUI.class` | `bc8997f2e1d0a3b60ab85d8391593a159da2f699ae2cc6b9bb37854aff5da6b4` | `68d3645c7f785ca92a889351534ec6e5fb0024cf4a867e1eda46f7e2dd051f96` | **36/36** |
| **Connected pair total** | | | **93/93** |

The original and independent-rebuild `javap -c -p -s` method and field declarations, descriptors, ordered opcodes, exact byte offsets, branch targets and resolved symbolic field/method references agree after normalizing **only** numeric constant-pool indexes. Exact `javap -p -constants` class surfaces also match; both generated classes target Java 9 classfile major 53. The complete original and recompiled binary class SHA hashes are **different**, so no full attribute/StackMapTable or byte-identical classfile parity is claimed.

Private connected two-class output pathname + compiled class hash manifest SHA-256:
`41d71ae6bc3721c23d42d09987179bf1608974d093bc5c4ff1d1d6a3572ce704`.

## Six original-versus-rebuilt pixel outcomes

A private isolated original-v311-JAR-versus-independently rebuilt **JDK headless Swing** test used three label strings (`Hello`, `Shadow UI`, `#ff00aa`) and two shadow color/offset settings (`Color.BLACK, Point(1,1)`; `Color(120,0,90), Point(-2,3)`). Each case checked the reflected public shadow-color/point accessors and the exact 160×40 full ARGB pixel SHA after invoking `JLabel.paint`.

**All 6/6 original-versus-rebuilt full raster hashes and getters matched**. Private six-case transcript SHA-256:
`da5ce03ad87197c8834ca0e8e873980bd0dcea025cd2e3b776c81f8892c6b388`.

These are bounded headless Java2D raster outputs using an installed JDK font, not the actual SpawnPK graphical client, game font/assets, GPU, account login or server.

## Cumulative v311 recovery and limits

The prior [three new original UI sources](V311_UI_PROGRESS_BUTTON_MOUSE_SOURCE_PARITY.md) raised documented original-v311 source recovery to **45 distinct classes / 2,130 ordered instruction matches**, spread across separate independently verified source builds. Adding this **two-class mutually connected Swing pair / 93 instructions** yields **47 distinct independently rebuilt original v311 classes / 2,223 matching original JVM instructions, across separate compilations**.

The five source classes reconstructed in this work session were also separately provided to the owner in a **private archive**, with the original/rebuilt SHA evidence and behavior-check source. This public repository contains none of that proprietary recovered Java.

The current source-recovery milestone is still **47/1,184 project classes**, not a complete independently source-buildable client, full classfile attribute equality, dynamic reflection/resource closure, or a verified game GUI. Nor is it one 47-class javac compilation.

## Public synthetic regression

`tests/test_v311_shadow_label_source_parity.py` uses **two independently authored synthetic JDK-only Java9 Swing classes**, a custom label and its UI delegate. It verifies they compile without an original game binary, that both explicit mutual `rs/` project dependencies are selected, that source recompile preserves ordered JVM declarations/instructions, and that six synthetic headless text raster cases match. A deliberate change of the synthetic shadow's horizontal offset must **fail** the verifier. Hosted CI cannot access and does not run the original game JAR or the private reconstructed pair.

**Next engineering focus:** dependency-closed UI rendering classes that consume the already recovered `rs/ui/components/d`, `w`, `a`, `x` and this shadow-label pair; then genuine scene-rendering support such as the original `rs/H` tile topology and `rs/V` scene roles. This is source recovery, not a request for historical R308 runtime/ZIP hunts.

# Original v311: stateful Swing panel + inherited layout interface source recovery

**Evidence date 2026-10-22.** Authentic original binary from the user's
private file library, exact SHA-256
`5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`.
Only hashes, public synthetic regression tests, and this report are committed.
The original JAR, original classfiles and private Java reconstructions stay
outside public GitHub.

## Two new original v311 Java reconstructions

| Original class | Exact original class SHA-256 | Independently built class SHA-256 | Original JVM instruction match |
|---|---|---|---:|
| `rs/ui/components/f.class` | `a1bb621c66408a11ac9b7e9ddc4b3bdb891712e280a4e85fc44e6fea811d5294` | `3b03a01d91c3d4f17b73ddacf01f16b53c4fe8f9a9f275b69d72bdfb97727c7d` | **84/84** |
| `rs/ui/components/q.class` | `8aa491819d87031af452dfaad452c98dafe4d276b121f2cd1c0a5e4f67610f30` | `361a66f260dda359a91c8980015f126780258264f4d8a95fe3fbc34310a6a33e` | **0/0; complete declaration/interface match** |
| **Additional 2** | | | **84/84** |

The `f` implementation is a Swing panel storing normal and darkened
foreground/background colors, with a boolean switch controlling which colors
are observed and installed. The `q` implementation is a UI layout interface
with a rectangle getter and overloaded point/dimension setters; it
**extends original `rs/ui/components/w`**, which was previously source-built.

The actual private Java sources compiled with `javac --release 9 -proc:none
-g:none`, empty game classpath/sourcepath, no original classes or runtime
resources supplied to the compiler. The original-vs-rebuilt `javap -p -c -s`
class/member declarations, descriptors, ordered JVM instructions, byte offsets,
branch destinations and resolved symbolic operands match, with only numeric
constant-pool indexes normalized. The rebuilt classfile SHA-256 differs from
the original, so complete classfile/StackMapTable equivalence is **not claimed**.

## Nine-class combined source build

The two newly recovered sources were compiled together with seven unchanged
previously recovered private sources:

- `rs/ui/components/f`, `q`, `w`, `x`;
- `rs/ui/components/shadowlabel/a` and `JShadowedLabelUI`;
- `rs/y/a`, `rs/y/b`, `rs/y/c`.

All **9 Java source files compiled into exactly 9 classfiles** in one
JDK-only Java9 build. **413/413** original ordered JVM instructions and
all class declarations matched. Previously recovered compiled SHA fingerprints
did not change. The SHA-256 of the ordered output manifest
`class/path + NUL + compiled-class-sha256 + newline` is
`39b70d93ecacc5100b97d188a7fcc929ca1bb513e7853972843264b2867b19ae`.

An isolated Java headless panel behavior comparison of original JAR and
recompiled private source used two RGBA colors and toggled four successive
mode states (false/true/false/true). For each state, the resulting flag,
foreground ARGB and background ARGB matched exactly. SHA-256 of the identical
four-state output transcript:
`e54f7c0eb18f09275d845afc9e3f0ace8dedaa22a204d2d7fabc6ce895736766`.
This does not test live gameplay or the actual game's UI/render assets.

A separately delivered **private owner-only source ZIP** contains all nine
Java files, exact original/rebuilt SHA manifest, and a verifier which compiles
them afresh and replays the original-vs-built declaration/instruction and
headless panel checks. Neither that archive nor any derived client binary
is committed to public GitHub.

The hosted test
`tests/test_v311_panel_interface_source_parity.py` uses an **unrelated
synthetic JDK-only** Java9 Swing panel plus two inherited interfaces to check
a three-class no-game-jar compile, exact symbolic instruction agreement and
four-state headless behavior. It must refuse a missing parent-interface
selection and a changed synthetic panel color operation. Hosted CI cannot
verify the authentic private reconstructed Java.

## Correct cumulative status

Prior verified authentic-v311 evidence: **47 distinct source-rebuilt original
classes / 2,223 matching original JVM instructions across separate source
build records**. Add these **two NEW classes / 84 instructions**:

**49 distinct classes / 2,307/2,307 matching instructions**, across
multiple builds, with a new independently certified **9-class** source
island. That is **not** one 49-class javac compilation, all 1,184 original
classes, full byte-identical classfiles, dynamic/resource dependency closure,
or gameplay certification. PR #1142 remains DRAFT/UNMERGED.

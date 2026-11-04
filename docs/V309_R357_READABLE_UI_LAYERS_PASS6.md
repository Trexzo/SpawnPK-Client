# R357 — Complete v309 source readability pass 6: infobox, login, texture and overlays

**Repository:** `Trexzo/SpawnPK-Client`; stacked on R356 draft PR #1149. R357 changes **owner-private reconstructed Java source only**. The original v309 client JAR, production v312, friends updater, cache, login information and live server are untouched.

## Measured private source baseline

Exact previous R356 source ZIP: `SpawnPK-v309-R356-Readable-Deobf-Pass5-Source.zip`, SHA-256 `e0fd993155ff4842ff35afa10e9dc77d47832e707b70f3dbac23427b9f423aa7`. Source member count **1,277**, each checked against its pinned SHA-256 in `PRIVATE_R356_READABILITY_MANIFEST.json` before any edit.

### Five source-supported, *inferred* Java class names

| Previous type | New readable type | Caller/implementation evidence |
| --- | --- | --- |
| `rs.ui.overlay.infobox.Class101` | `InfoBoxImageSizingMode` | InfoBox stores a two-value mode; InfoBoxManager chooses full versus reduced image scale from the value |
| `rs.graphics.login.Class68` | `LoginScreenView` | Two-value login UI view state, selected by LoginScreen and Client |
| `rs.graphics.preview.support.Class56` | `TextureDebugSection` | TextureDebugLoader switches sections for `[textur]`, `[random]` and `[recolor]` headings in debug/textures.txt |
| `rs.graphics.overlay.actor.Class67` | `ModelInspectorOverlayBase` | Abstract Overlay subclass supplied an entity and model by OverlayManager; RecolorInspectorOverlay extends it |
| `rs.graphics.overlay.npcmarker.Class63` | `NpcMarkerSpriteOffset` | Stores sprite index plus NPC-relative X/Y/height adjustments consumed by NpcMarkerOverlay |

Nine directly related fields have been renamed: `InfoBox.imageSizingMode`, `LoginScreen.currentView`, the model-inspection overlay's `inspectedModel` / `inspectedEntity`, and marker `spriteIndex` / `offsetX` / `offsetY` / `heightOffset` / `ownerOverlay`. Five method aliases are also made readable: `getImageSizingMode`, `setImageSizingMode`, `setCurrentView`, `setInspectedModel`, `setInspectedEntity`.

No enum constant values, packet opcodes, protocol field layouts, executable logic or string-literal content were deliberately changed. **5 types + 9 fields + 5 methods** form **19 inferred name candidates** and **108 witnessed lexical identifier edits**. Original class/field/method names and exact per-path occurrence counts are in `scripts/prepare_v309_r357_readable_ui_layers.py`; exact original declaring Java owner SHA pins are checked too.

**All 1,277 previous source files were restored byte-for-byte by reversing only the recorded positions of edits.** This is an exact source-text inverse proof, not a proof of runtime/JAR-level equivalence.

## Independent real complete-source clean builds

The entire private R357 candidate was compiled using JDK 21 targeting Java 11 with `javac --release 11 -proc:none -g:none`:

- Java sources: **1,277**
- Emitted project classfiles: **1,386**
- Original `rs/` game project classes in dependency JARs: **0**
- Compile result: **exit 0**, with only deprecated/unchecked usage warnings
- Deterministic source-built Java JAR SHA-256: **`ca3f1f2dc91869fbff6f29d4e8a3e3d529c15071b9bb8be8f2779e24ebb2e90c`**

A new, self-contained offline build kit was independently extracted into a **separate fresh working directory**. Running its bundled `tools/rebuild_from_source.py --output fresh-rebuilt.jar` produced the *identical* **1,386 classes and JAR SHA** (exit 0).

Private user downloads (not public GitHub release attachments):

| File | SHA-256 | Bytes |
| --- | --- | ---: |
| `SpawnPK-v309-R357-Readable-Deobf-Pass6-Source.zip` | `9cd9d3ccd2287d7f0fcd917b57c1e0148f803c930499ebac6ada6efe40b31c55` | 1,929,783 |
| `SpawnPK-v309-R357-Readable-Pass6-Reproducible-Build-Kit.zip` | `819079b29ea90e84f2a15a53430d4a68651e2614f860d51d2ff3e024c2e32753` | 19,838,223 |

The public repository contains only the reproducible name-mapping tool, fake miniature synthetic tests and review evidence, **not raw private recovered Java or binary dependencies**. Real source compilation was performed privately; GitHub CI cannot itself attest to the private-source compile.

## Reproducible source transformation

```powershell
py -3 scripts/prepare_v309_r357_readable_ui_layers.py `
  --r356-private-source "C:\private\SpawnPK-v309-R356-Readable-Deobf-Pass5-Source.zip" `
  --new-private-source "C:\private\SpawnPK-v309-R357-Readable-Source.zip"
```

The script refuses an incorrect archive SHA, mismatched inner source members or SHA-256, unsafe/symlink/traversal filenames, an already existing destination, any unexpected symbol references or reference counts, source type declaration changes, destination class collisions and imperfect byte-exact reversal. Hosted CI uses **synthetic Java snippets only**.

## Remaining deobfuscation frontier

| Lexical measure | R356 | R357 |
| --- | ---: | ---: |
| Obfuscated `Class<number>.java` filenames | 286 | **281** |
| Java files with `field<number>` tokens | 883 | **881** |
| Java files with `method<number>` tokens | 806 | **805** |

**Original v309 source/JVM semantic parity, reflection/name dependencies, public Source-M1 publication and real gameplay runtime equivalence are still not established.** These remain inferred candidate names and the PR must stay **DRAFT / UNMERGED**.

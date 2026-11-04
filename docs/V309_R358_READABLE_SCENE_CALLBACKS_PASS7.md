# R358 — readable v309 Java source pass 7: scene overrides and callback APIs

**Correct project:** `Trexzo/SpawnPK-Client`. This work builds on R357 PR #1150 and its owner-private full Java source tree. It does not modify the production v312 client, updater, original v309 game JAR, cache or server.

## Actual R357 source input and provenance

- Input source archive: `SpawnPK-v309-R357-Readable-Deobf-Pass6-Source.zip`
- Input SHA-256: `9cd9d3ccd2287d7f0fcd917b57c1e0148f803c930499ebac6ada6efe40b31c55`
- All **1,277** Java files independently checked against `PRIVATE_R357_READABILITY_MANIFEST.json` before modification.
- `research/v309-source-recovery/r358-readability-input-witness.json` pins SHA-256 of all nine original declaring Java files and exact reference paths/counts for all 21 symbols. The complete mapping covers **117** identifier occurrences.

## Inferred descriptive class identities

| Obfuscated class | New candidate name | Grounding from recovered Java |
| --- | --- | --- |
| `rs.definitions.Class42` | `SceneObjectOverrideRecord` | Mutable object ID, X/Y tile coordinates, plane and placement parameters read by `SceneObjectScriptPacket` |
| `rs.definitions.Class43` | `SceneObjectOverrideRegistry` | Location-indexed map and replay of object overrides in client scene; referenced from `Client` and script packet |
| `rs.ui.components.Class99` | `ComponentReorderListener` | Functional callback invoked after `DragAndDropReorderPane` completes reordering |
| `rs.runelite.api.Class302` | `EntityDrawCallback` | `draw(model,boolean)` callback shared by entity-hider and hidden-player plugins and `EntityDrawCallbacks` registry |
| `rs.gpu.Class113` | `SkyboxColorSampler` | Three-integer pixel/position callback used to sample color during `SkyboxDefinition` rendering |
| `rs.util.Class80` | `HeavyweightPopupFactory` | Overrides `PopupFactory.getPopup(...,boolean)` and forces the heavyweight flag; `UiUtils` installs it as shared factory |
| `rs.gui.loadouts.dialogs.Class131` | `CreateLoadoutActionListener` | `ActionListener` registered on `CreateLoadoutAction`, delegates to parent action |
| `rs.gui.loadouts.dialogs.Class140` | `DismissLoadoutDialogListener` | `ActionListener` registered on input-dialog button; hides and disposes `LoadoutInputDialog` |
| `rs.util.Class83` | `ClassLoaderLookupBridge` | Interface offering `defineClass`-style bytecode definition and `MethodHandles.Lookup` install/retrieval used by `Class84`/`Class85` |

Seven scene-object fields were given descriptive inferred names: `objectId`, `tileX`, `tileY`, `plane`, `objectRotation`, `objectType`, `overridesByLocation`. Five methods were renamed: `onComponentReordered`, `sampleSkyboxColor`, `defineClassBytes`, `getMethodHandlesLookup`, `installMethodHandlesLookup`. The field orientation/type names remain **inferences from observed parameter order**, not original-author documentation.

**Total:** **9 classes + 7 fields + 5 methods = 21 symbols**, **117** lexical identifier changes in **22** existing Java files. Nine declaring Java paths changed. No packet IDs or gameplay branches were intentionally modified.

## Real full-source and independent fresh-kit build

- Private R358 Java source ZIP: `SpawnPK-v309-R358-Readable-Deobf-Pass7-Source.zip`
- ZIP SHA-256: `95f4319993bce5988d47d34f76709d96e72e8b0d59b319d406fa773be748cb68`
- All 1,277 sources compiled with **JDK21**, `javac --release 11 -proc:none -g:none`, with explicit empty sourcepath.
- Actual result: **exit 0**, **1,386** game/client classfiles.
- Both pinned dependency JARs checked: **0** precompiled `rs/` game client classes (no project-binary fallback).
- Deterministic compiled R358 client-candidate JAR SHA-256: **`1735001265dcd20df107dfffbe9643862fcc2145483e37d2506803c372161ff4`**.
- A newly packaged complete private build kit was extracted to a **separate fresh temporary directory**; its bundled `tools/rebuild_from_source.py` independently reproduced the **same 1,386 classes and identical candidate JAR SHA**.
- Kit: `SpawnPK-v309-R358-Readable-Pass7-Reproducible-Build-Kit.zip`
- Kit SHA-256: `b34d5ea48fb27d7cce413ceb847f6da002bf95165b6387152026632b32836c1a`.

The **entire previous R357 source tree** is reconstructed **byte-for-byte** when the 21 renames are undone in recorded reverse edit-position order. This proof preserves pre-existing matching readable words in literals. It does not certify original v309 bytecode/control-flow/reflective-name equivalence.

## Exact reproducibility in public GitHub tooling

The PR commits:
- `scripts/prepare_v309_r358_readable_scene_callbacks.py` — validates the full archive SHA, per-file SHA, safe ZIP paths, original class owner hashes, **exact reference paths and counts**, 117 edits, path collision rejection and exact inverse; refuses an existing output path.
- `research/v309-source-recovery/r358-readability-input-witness.json` — 21 source reference inventories and 9 owner hashes.
- `tests/test_v309_r358_readable_scene_callbacks.py` — synthetic examples, including a dependent pair of renamed classes and original-name literal preservation; no raw private source.
- `.github/workflows/v309-r358-readability.yml` — Windows/Ubuntu Python3.11/3.12 synthetic regression CI.

Private reproduction, assuming the R357 source archive is available on the owner machine:

```powershell
py -3 scripts/prepare_v309_r358_readable_scene_callbacks.py `
  --r357-private-source "C:\private\SpawnPK-v309-R357-Readable-Deobf-Pass6-Source.zip" `
  --witness "research/v309-source-recovery/r358-readability-input-witness.json" `
  --new-private-output "C:\private\SpawnPK-v309-R358-Readable-Source.zip"
```

Private reconstructed Java, binary dependencies and source-built JAR remain **outside this public repo** until the existing Source-M1 acceptance gates are satisfied. GitHub CI tests synthetic cases, not the private real full-source compilation.

## Deobfuscation frontier

| Lexical source metric | R357 | R358 |
| --- | ---: | ---: |
| Numeric `Class<number>.java` filenames | 281 | **272** |
| Files containing `field<number>` | 881 | **878** |
| Files containing `method<number>` | 805 | **801** |

Of the initial 307 numeric class filenames, **35 have received inferred readable names** in this track. The remaining 272 and numerous numeric fields/methods require further work.

All renames remain **INFERRED CANDIDATES**, not original-author symbol proof, a certified Source-M1 public release, or runtime/untouched-JAR parity. Keep the PR **DRAFT / UNMERGED**.

# R355 — readable original-v309 source candidate, outline + NPC naming pass 4

**Repository:** `Trexzo/SpawnPK-Client`, stacked on R354 draft PR #1147. This is a private recovered-source workflow. No production v312, friends updater, original JAR, account or live server has been modified.

## Source evidence and naming

Input is the exact R354 1,277-source private ZIP `SpawnPK-v309-R315-Readable-Deobf-Pass3-Source.zip`, SHA-256 `e515f96d753a8e0458c21b7a4ebf16c080411ea3ddbf85d184022497bfffd768`. Every Java file is checked against its own R354 inner source hash manifest. This is reconstructed Java, not author-original source text.

| Original Java type | Inferred readable name | Grounding from private R354 source |
| --- | --- | --- |
| `rs.ui.outline.Class102` | `OutlinePixelBlockPool` | Grows and reuses fixed 1,024-int pixel-coordinate blocks via an index/free-list pool, used by `SimpleClientOutline` |
| `rs.ui.outline.Class103` | `OutlineKernelOffset` | Stores X/Y offsets used to rotate/reflect circular outline convolution offsets |
| `rs.ui.outline.Class104` | `OutlineWeightedSample` | Carries radial distance, offset into output raster, and alpha attenuation weight |
| `rs.plugins.npcindicators.Class276` | `HighlightedNpcBuilder` | Builder-like methods accumulate NPC, colors and render settings; constructs `HighlightedNpc`, and `toString()` already prints `HighlightedNpc.HighlightedNpcBuilder` |
| `rs.scriptpacket.handler.Class264` | `NpcHeadIconOverridePacketHandler` | Registered as script packet **43**, updates a map keyed by NPC definition ID; `rs.Client` uses entries to override `npcDefinition.headIcon` for prayer-head-icon sprite rendering |

Member candidates: `Class102.field5559/5560/5561` → `packedCoordinates/freeBlockIndices/freeBlockCount`; `Class103.field5562/5563` → `offsetX/offsetY`; `Class104.field5564/5565/5566` → `radialDistance/pixelOffset/alphaWeight`; `Class264.field4118` → `npcHeadIconOverrides` (updated in both declaring handler and `rs.Client`).

These are **5 inferred type names + 9 inferred field names = 14 symbols**, with **111 identifier replacements** in **9 unique source files**. No existing protocol opcodes, methods, expressions, control-flow branches or literal Java source strings are deliberately changed. Five source filenames were changed.

## Exact source reversibility

R355 records each individual edit position in the post-replacement text; inverse edits use those positions in reverse transformation order. This is important because the pre-existing literal `"HighlightedNpc.HighlightedNpcBuilder(npc="` contains a readable name before the rename: a naive global reverse replacement would corrupt that original string. The exact-position inverse recovered **all 1,277 R354 source files byte-for-byte**, including that pre-existing literal and unrelated classes.

The source tree remains **1,277 files**, now with **293** `Class<number>.java` filenames remaining (R354: 298). Names are `INFERRED_CANDIDATES`, not authenticated original-author identifiers or original-JAR parity.

## Actual private compile and independent rebuild

The entire R355 private tree was compiled from 1,277 Java files using the JDK 21 `javac --release 11 -proc:none -g:none`, JAR output rebuilt deterministically, zero `rs/` project binary fallback. **Result: exit 0, 1,386 classfiles**. Each of the two private dependency JARs contains **zero `rs/` game classfiles**.

A self-contained owner-private kit was generated and extracted to an independent fresh workspace, whose embedded `tools/rebuild_from_source.py` was executed. **Exit 0, same 1,386 compiled classes and identical candidate JAR SHA-256**:

`99525b39b522474ff103a14fc884ab432d56580dd0dad39c9a192afae17c7c1d`

The JAR hash attests to the candidate *source-rebuilt artifact*, **not** equivalence with the untouched original v309 10,502-class JAR. No authenticated login, rendering or runtime parity was tested in this pass.

### Private owner deliverables (not public GitHub attachments)

| Artifact | SHA-256 | Content |
| --- | --- | --- |
| `SpawnPK-v309-R315-Readable-Deobf-Pass4-Source.zip` | `7b58b0cc0292aa1a573ff2d1b940eb92fbbb0c7676b9cfdb4931b6824d00ad2c` | 1,277 Java files, R355 SHA/provenance manifest |
| `SpawnPK-v309-R355-Readable-Pass4-Reproducible-Build-Kit.zip` | `bd0281277a3d87e93d5977647d51b7d9953d28e378f9fcf9ba4e915f5232700d` | Source, two pinned dependency-only JARs, reproducible offline script |
| `SpawnPK-v309-R355-Readable-Pass4-Receipt.json` | `153ab8219fba51bca5b9916bfc993560af0a77752ab29f842133a9fa8726a4a8` | Source count, build SHA, exact inverse, source hashes |

## GitHub reproducibility and restrictions

`scripts/prepare_v309_r355_readable_outline_npc.py` enforces R354 archive SHA, the full 1,277 per-Java SHA-256 map, exact original declaring owner SHA, reference location/count, safe ZIP paths, complete source set and a never-reused destination. It creates a new private source ZIP with the inferred name changes and a manifest, and proves byte-exact inverse in memory.

```powershell
py -3 scripts/prepare_v309_r355_readable_outline_npc.py `
  --r354-private-source "C:\private\SpawnPK-v309-R315-Readable-Deobf-Pass3-Source.zip" `
  --new-private-source "C:\private\SpawnPK-v309-R355-Readable-Source.zip"
```

The public cross-platform GitHub tests run only **synthetic small Java cases** (including pre-existing readable-name literals) and fail-closed negative controls. Raw recovered client source, private dependencies, original JAR and game caches remain outside GitHub and CI. The current Source-M1 publication/semantic identity gate is **not yet satisfied**.

**Next:** Prioritize additional well-grounded class name groups and method/field names, then verify descriptor-level original-JAR parity and reflection-sensitive references. Keep this PR **DRAFT / UNMERGED**.

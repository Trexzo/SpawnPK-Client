# R361 — original-v309 candidate source, readable loadout model and persistence pass 9

**Correct repository:** `Trexzo/SpawnPK-Client`, stacked on R360 PR #1153, which was stacked on R359 PR #1152. This is the full 1,277-Java-source *candidate* recovery, not the separate original-client-runtime diagnostic track. This PR is public **tooling, synthetic tests, source-hash witnesses and evidence only**, not private recovered client source.

## Pinned source and bounded edit

Owner-private R359 readable Java source ZIP: `SpawnPK-v309-R359-Readable-Deobf-Pass8-Source.zip`, SHA-256 **`31d4612bce93fc1ce30964a893d8df96d5feca7464569071daa4b2995024d5c4`**. Exactly **1,277 source members** and the R359 private SHA manifest were read and checked before transformation. Declaring-type SHA-256 pins and the exact corpus-wide path/count census of 23 original symbols are stored in `research/v309-source-recovery/r361-loadout-state-readability-witness.json`.

**23 inferred renames = 11 fields + 12 methods; 96 Java-token occurrences across 9 Java files.** All 1,277 transformed files reversed **byte-for-byte** to the pinned R359 input. Java comments, string and character literals were not edited.

### Loadout model

| Numeric identifier | Inferred readable identifier | Source evidence |
| --- | --- | --- |
| `field3273`, `method2629`, `method1824` | `primaryPetItemId`, `getPrimaryPetItemId`, `setPrimaryPetItemId` | Clone copies client pet field; equipment panel draws item; spawn builds `::pet_loadout` command |
| `field3274`, `method1183`, `method1270` | `secondaryPetItemId`, `getSecondaryPetItemId`, `setSecondaryPetItemId` | Second pet in same command, sprite and clone state |
| `field3275`, `method6`, `method1575` | `prayerBookMode`, `getPrayerBookMode`, `setPrayerBookMode` | 0/1 chooses normal prayer or curses icon and command |
| `field3276`, `method456`, `method966` | `cosmeticItemId`, `getCosmeticItemId`, `setCosmeticItemId` | Clone copies local player cosmetic ID; `::equip_loadout` command and equipment panel image |

### LoadoutStore filesystem/model coupling

| Numeric identifier | Inferred readable identifier | Source evidence |
| --- | --- | --- |
| `field3259` | `owningLoadoutsPanel` | Store constructor receives the panel; folder-order writer queries its folders |
| `field3260`, `field3261`, `field3262` | `loadoutTempPath1`, `loadoutTempPath2`, `loadoutTempPath3` | Constants concatenate `loadout_temp`, `loadout_temp_2`, `_3` |
| `field3263` | `defaultLoadoutConfigPath` | Constant path ends in `loadout.conf` |
| `field3264` | `orderSettingsFilename` | Constant literal `order.settings` |
| `field3265` | `folderOrderSettingsPath` | `loadoutsDir + File.separator + order.settings` |
| `method3561` | `resolveFolderDataPath` | Chooses specific loadout folder file or `loadout.conf` |
| `method1997` | `resolveLegacyTempPath` | Resolves one of the temporary loadout file paths |
| `method955` | `deleteFolderDataFiles` | Removes folder data and temp files during folder deletion |
| `method2767` | `writeFolderOrderSettings` | Writes ordered folder names, one per line, to `order.settings` |

Names are **inferred from reconstructed source**; these are not verified original-author names. No serializer structure, ordering, settings path values, network packet behavior or game logic was changed. The recovered Java may itself contain unrelated defects; this readability pass does not fix them.

## Real private compilation (not GitHub CI)

- JDK **21.0.12.1** `javac --release 11 -proc:none -g:none`, 1,277 private Java files → **1,386 compiled classfiles**, exit 0.
- R359 pinned dependency JARs unchanged; neither contains `rs/` game class fallback.
- Candidate compiled JAR SHA-256: **`c69c099c89f06271f38def24a01ac723bdb9101598cf4b103bf60e6b868a39b4`**.
- Independent fresh extraction/rebuild of the R361 private kit: exit 0, 1,386 classfiles, **same exact JAR SHA-256**.
- Private R361 output source ZIP / private build-kit SHA-256 are recorded in the owner handoff; **neither is committed to public GitHub**.
- **18 local synthetic regression tests PASS** (archive SHA refusal, exact inverse, Java token boundaries, literal/comment preservation, witness tampering, target collisions, output clobber protection).

## Offline reproduction

```powershell
py -3 scripts/prepare_v309_r361_readable_loadout_state.py `
  --r359-private-source "C:\private\SpawnPK-v309-R359-Readable-Deobf-Pass8-Source.zip" `
  --witness "research/v309-source-recovery/r361-loadout-state-readability-witness.json" `
  --new-private-output "C:\private\SpawnPK-v309-R361-Readable-Source.zip"
```

CI only uses synthetic inputs, Windows + Ubuntu and Python 3.11/3.13. It cannot attest the owner-private full build or original binary without private artifacts. The original-v309 JAR has **not** been run in this batch. Source M1 publication gate is unchanged; **draft/unmerged**, no production v312 client or updater change, no original cache, credentials or server contact.

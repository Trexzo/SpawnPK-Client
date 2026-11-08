# R363 — full v309 readable Java candidate, pass 11: loadouts panel UI

**Repository:** `Trexzo/SpawnPK-Client`, stacked draft after R362 PR #1155. **Keep draft/unmerged.** This is owner-private, recovered v309 *candidate* source. The original JAR, production v312, updater, caches and servers are unchanged.

## Private input and exact reversible transform

- R362 readable source archive SHA-256: `f7b3d76a747b99accf33e8088eccfb5d32c7018ab25473d7430fe3f7190f6183`.
- 1,277 Java sources validated against each SHA-256 from `PRIVATE_R362_READABILITY_MANIFEST.json` before editing.
- Declaring source SHA-256: `rs/gui/loadouts/LoadoutsPanel.java` = `fa58325efa1b1310c42bcf71106393ff9e89c1a6c5121602cecb7bffd17702c9`.
- Public proof file `research/v309-source-recovery/r363-loadout-panel-readability-witness.json` pins token counts across the **entire** 1,277-file corpus.
- 2 field renames + 7 method renames = **42 Java identifier occurrences in six source files**. The source-aware lexer excludes comments, string literals and char literals.
- Exact inverse restored **all 1,277 R362 source files byte-for-byte**. No Java behavior or data serialization was intentionally altered.

## Inferred names grounded by implementation

| Original | New candidate name | Source-observed reason |
| --- | --- | --- |
| `field3305` | `folderMenuButton` | JButton bound to the “Loadout folders” context menu |
| `field3306` | `activeStatEditorDialog` | current `StatEditorDialog` instance, disposed/nullified by close method |
| `method812()` | `rebuildFolderPopupMenu()` | assigns `FolderPopupMenu.createPopup(this)` |
| `method2809()` | `resetLoadoutSelector()` | calls `method3472(0)` to select index 0 |
| `method3472(int)` | `rebuildLoadoutSelector(int)` | updates JComboBox model based on active folder's loadouts |
| `method1976()` | `requestLoadoutRepaint()` | calls `Launcher.getInstance().scheduleRepaint(20, true)` |
| `method1483()` | `getFolderMenuButton()` | returns the folder-menu JButton |
| `method3578()` | `disposeStatEditorDialog()` | disposes/nulls editor dialog if present |
| `method1012()` | `buildControlRows()` | constructs two JPanel UI control rows |

The inferred names **are not verified original-author identifier names**, and changing source identifiers does not establish original-v309 JVM descriptor identity, reflection equivalence or runtime parity.

## Important semantic audit findings, intentionally **not** fixed

1. `LoadoutFolders.saveLoadout(String,String)` **removes a loadout from a folder** and removes it from the selection box; a misleading pre-existing name. It is called by `SaveLoadoutAction` in a delete-confirmation flow. Renaming this nonnumeric API requires separate callsite/reflection compatibility assessment.
2. `LoadoutFolders.moveFolder(String,int,int)` actually **swaps two loadouts within one named folder**, not folders. Its public API was not changed.
3. `LoadoutSerializer.read(DataInputStream,LoadoutList)` iterates with `do { ... } while (var3 != null)` where `var3` is assigned a newly created nonnull `String`. The enclosing data-reader relies on EOF handling. The method also uses `DataInputStream.read(byte[])`, for which partial reads are possible. No format/behavior changes were attempted.

These are **potential correctness/reliability concerns**, not evidence that the original client is exploitable. A name-only pass should not change legacy serialization behavior.

## Private offline build verification

- `javac` from **OpenJDK 21.0.12.1**, `--release 11 -proc:none -g:none`, compiled **all 1,277 Java files** with zero errors into **1,386 class files**.
- Two pinned non-`rs/` dependencies from the R362 build kit were retained, unmodified.
- Deterministically packaged candidate JAR SHA-256: `8610e34d9783876de973f3688311a4210bfa959aa5bf2ec6d5443f28c74cc32b`.
- Two independent fresh extractions of the private R363 build kit and complete offline rebuilds produced **the exact same JAR SHA-256**.
- Private source ZIP SHA-256: `035837ec988fff706bbfb241e593277e8a5c39c448821982667a33b26f990450`.
- Private reproducible build kit ZIP SHA-256: `7beb05469259266eccbae0e02a7a723552d11dc2e551bba3756b8c1c9ce25a1e`.
- Public synthetic regression tests: **20/20 PASS** locally. Hosted CI result separate.

## Publication and runtime gate

The public PR contains only the preparer script, source-path/hash witness, synthetic tests, this document and CI workflow. **The 1,277 Java source files, dependency JARs, complete private build kit, source-built candidate JAR and original v309 JAR remain private.** No original game client launched, no live login or same-PID reconnect tested, no v312 modified. Source-M1 release gate remains **closed**.

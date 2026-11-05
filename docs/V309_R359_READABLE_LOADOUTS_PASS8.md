# R359 — v309 readable Java source pass 8: loadout dialogs and input controls

**Target repository:** `Trexzo/SpawnPK-Client`, stacked on R358 PR #1151. This is the **complete, 1,277-Java-source candidate** path, not the separate `fullspkclient-private` runtime testing track. The original v309 client JAR, production v312, its updater and all user cache/credentials remain untouched.

## Original source baseline and new lexer safety

Input is the owner-private R358 Java archive `SpawnPK-v309-R358-Readable-Deobf-Pass7-Source.zip`, SHA-256 `95f4319993bce5988d47d34f76709d96e72e8b0d59b319d406fa773be748cb68`. All **1,277** inner source SHA-256 values are checked before edits.

This pass improves on previous lexical substitutions with a **Java-aware identifier scanner**. It ignores `//` and `/* ... */` comments, Java string and character literals, and rejects malformed quoted literals / unsupported Java text blocks. It scans the full source corpus once to enumerate all references, then allows only the exact expected source file/count for each symbol. Edits are tracked by position so an inverse transforms every file to its prior exact bytes without replacing unrelated preexisting readable identifiers.

Java source is private; the public repo contains this tool, hashes/reference witnesses, synthetic tests and this evidence report, **not the raw reconstructed client source or binary dependencies**.

## Sixteen inferred readable class names

| Previous class | Readable candidate | Source-grounded role |
| --- | --- | --- |
| `rs.gui.loadouts.Class124` | `LoadoutContextMenuMouseListener` | Opens LoadoutsPanel context menu on mouse release |
| `rs.gui.loadouts.Class125` | `CloseLoadoutsWindowAction` | Hides and disposes an existing loadouts JFrame |
| `rs.gui.loadouts.dialogs.Class126` | `CloneEquippedLoadoutAction` | Copies equipped inventory, equipment and spellbook from active client into loadout |
| `Class127` | `CancelCloneLoadoutAction` | Cancels clone dialog and disposes JFrame |
| `Class128` | `CloneLoadoutButtonFactory` | Creates the Clone JButton and attaches CloneLoadoutAction |
| `Class129` | `LoadoutColorListCellRenderer` | Uses per-row color arrays to render combo/list options |
| `Class130` | `LoadoutListCellRenderer` | Draws folder loadouts with their custom colors and tag icons |
| `Class132` | `ConfirmCreateLoadoutAction` | Creates loadout, assigns tag/color and updates the selected folder |
| `Class133` | `LoadoutTagListCellRenderer` | Chooses LoadoutTag icons while rendering items |
| `Class134` | `LoadoutFolderPopupListener` | PopupMenuListener repaint/selection lifecycle for folder list |
| `Class135` | `LoadoutFolderComboBox` | JComboBox of loadout folders with custom renderer and action listeners |
| `Class136` | `ConfirmCreateFolderAction` | Reads folder-name text and creates folder |
| `Class137` | `ConfirmRenameFolderAction` | Reads name and renames selected folder |
| `Class138` | `ConfirmDeleteFolderAction` | Deletes folder by name and closes confirmation window |
| `Class139` | `CancelDeleteFolderAction` | Disposes delete confirmation without deleting |
| `Class141` | `SpawnLoadoutButtonFactory` | Creates Spawn Loadout JButton and SpawnLoadoutAction |

Class names are **inferred from reconstructed source semantics**. The source tree is not verified original-author text, and the name changes do not constitute original-JAR semantic identity proof.

## Thirteen inferred field/method names

Seven numeric fields renamed: `field3196`→`optionColors`, `field3197`→`optionLabels`, `field3198`→`colorComboBox`, `field3199`→`loadoutFolders`, `field3200`→`folderComboBox`, `field3205`→`tagComboBox`, `field3209`→`loadoutFolders` in their respective declaring classes.

Six numeric methods renamed: `method1944`→`setOptionColors`, `method1119`→`setOptionLabels`, `method1436`→`getOptionColors`, `method1503`→`getOptionLabels`, `method3063`→`createCloneLoadoutButton`, `method994`→`createSpawnLoadoutButton`.

**29 symbol renames / 107 Java-token identifier changes**, affecting **24 logical source compilation units** (16 declaring filename changes). `research/v309-source-recovery/r359-loadout-readability-witness.json` pins each original declaring file SHA and exact reference counts. A measured inverse confirmed **1,277/1,277 original R358 Java files restored byte-for-byte**. String literal and comment bytes were preserved by the Java lexer.

## Full-source clean build and independent replay

Real private build on this R359 source tree:

- `javac` from **OpenJDK 21.0.12.1**, `--release 11 -proc:none -g:none`
- **1,277 Java sources** compiled, **exit 0**, yielding **1,386 compiled client classfiles**
- Both pinned dependency JARs contain **zero `rs/` game classes** — no compiled SpawnPK class fallback
- Deterministically packaged R359 candidate JAR SHA-256 **`129fe448016f380d712028b1917879a135b99f91ebad93186d4e4cdaebda63ee`**
- A complete offline build kit was independently extracted into a fresh temporary directory and its `tools/rebuild_from_source.py` run. **Exit 0, 1,386 classfiles, exact same JAR SHA**.

Source-only ZIP: `SpawnPK-v309-R359-Readable-Deobf-Pass8-Source.zip`, SHA-256 `31d4612bce93fc1ce30964a893d8df96d5feca7464569071daa4b2995024d5c4`.

Self-contained owner-private kit: `SpawnPK-v309-R359-Readable-Pass8-Reproducible-Build-Kit.zip`, SHA-256 `1d2d8394d1002393fecbb9d9e54a03bf136e1c5e65295a13962c27a7929a815f`. It includes all 1,277 Java files, two pinned non-project dependencies, the build script and exact source/JAR SHA manifest.

This compiled JAR is a **readable source candidate**, not the untouched original v309 binary or proven runtime-equivalent client.

## Reproducible private command

```powershell
py -3 scripts/prepare_v309_r359_readable_loadouts.py `
  --r358-private-source "C:\private\SpawnPK-v309-R358-Readable-Deobf-Pass7-Source.zip" `
  --witness "research/v309-source-recovery/r359-loadout-readability-witness.json" `
  --new-private-output "C:\private\SpawnPK-v309-R359-Readable-Source.zip"
```

The script refuses mismatched archive SHA, missing/changed Java source bytes, unsafe ZIP members, unexpected owner hashes or reference counts, class filename collisions, source count drift, literal/comment parsing issues, failing inverse or an existing destination. Hosted Windows/Ubuntu CI uses **synthetic Java-only tests**; actual private source compilation is reported from the independently executed offline build, not from public hosted CI.

## Remaining readable-source frontier

| Metric | Before R359 | After R359 |
| --- | ---: | ---: |
| Numeric `Class<number>.java` filenames | 272 | **256** |
| Java files containing numeric field names | 878 | **876** |
| Java files containing numeric method names | 801 | **798** |

**51 of the initial 307 numeric-class filenames have now received inferred readable names.** Full semantic deobfuscation, original-v309 class/descriptor parity, reflection-sensitive string audits and runtime equivalence remain to be established. Keep PR **DRAFT / UNMERGED** under the existing Source-M1 gates.

# SpawnPK v309 R299 — seven authentic Scene mutation bounds guards

**2026-10-20. Actual private client-source fix and source-built Java tests.** Sole active PR #1142 stays DRAFT. No original complete client, source tree, cache, assets, fonts, credentials or proprietary JAR uploaded to public GitHub; nothing installed on the owner PC or merged to `main`.

## Root cause, actual RED test

R298 fixed read-only `Scene` object queries but seven small scene-update methods still indexed `this.tiles[plane][x][y]` **before** validating the plane or coordinates. The **actual R298 1,386-class JAR** fails the new regression when invoking `Scene.method251(-1,50,50,1)`:

```text
R299_SCENE_MUTATION_BOUNDARY_CRASH method=method251 scene=-1,50,50
java.lang.ArrayIndexOutOfBoundsException: Index -1 out of bounds for length 4
```

This is a new lower-level mutator crash path, separate from R290/R293 object-click checks, R295 `getHashAtTile`, and R298 read-only queries.

## Production source change, precisely scoped

On exact R298 recovered `source/rs/Scene.java` SHA256 **`1999066509802862ba8c7ba0e4d54cabdf0cf8da64aabbc370439eda287ceada`**, one bounds helper `isSceneTileInBounds(plane,x,y)` is added before the existing read-only `safeQueryTile` helper. Exactly **seven** existing, small scene-update methods now refuse invalid coordinates **before any tile lookup**:

- `method251`
- `method3478`
- `method93`
- `method1252`
- `method1390`
- `method1152`
- `method1627`

Each original method uses a possibly different argument ordering; the patch maps each plane/X/Y separately. In-bounds behavior is unchanged, including `method251` mutating a real Tile and `method93`'s legacy byte-dependent side effect. Invalid coordinates now cause a no-op, not a crash or side effect. No scene renderer, cache, networking, protocol opcode, object definitions, login, collision path, or broader mutators altered.

SHA256 of exact resulting `Scene.java`: **`007159b0b47058552150985c45f5b441df1a4bbd5a794bc41b6ad172bee8832e`**. Rebuild recipe rejects unexpected source preimage/postimage, duplicate/missing anchors, private owner archive hash drift and existing output paths.

## Real compiled-client regression and deterministic build

Original owner-private R278 and R265 input ZIPs byte-verified; all **1,277** original Java files compiled with `javac --release 11` into **1,386 compiled classes**, twice independently. R299 JAR SHA256 from both builds, **identical byte-for-byte**:

```text
9c4d4350918c05c4a9f40d9372cab8c77088c76a43a32eb7f46b6974d57738cc
```

Direct class comparison with the exact R298 class JAR: **only `rs/Scene.class` changed**. All other 1,385 compiled classes are identical.

**Genuine real-client Java regression:**
- R299 new Java suite: **136/136** PASS, seven methods × fifteen invalid coordinate/plane cases + four valid empty tiles, plus checks that valid Tile mutation persists, invalid byte-dependent toggle has no side effect, and valid toggle remains intact.
- R298 original scene-query suite: **192/192** PASS.
- R295 original scene-hash suite: **69/69** PASS.
- R293 original object-menu suite: **71/71** PASS.
- **Total 468/468 actual Java assertions** across new and previous real-class suites. Original R298 fails the R299 regression (real red witness); no fake test fixture or synthetic Java production class substituted.

## Authentic GUI replay — actual but limited scope

One isolated Linux/Xvfb 1400×900 run used a **disposable copy of the prior SHA-verified 10,772-file R298 original cache/test home**, replacing its private compiled class JAR with **only** the SHA-verified R299 class JAR; the original R285 bounded Java Robot + 127.0.0.1 synthetic-server source retained. This is **not** a second independent from-archives staging or a native Windows acceptance. The original R298 binary was absent from the disposable test home.

The actual R299 GUI run **returned native `xvfb-run` exit code 0** and `R285_SESSION_TERMINATED status=PASS`, rendered original OSRS region **13386 / field1134**, and used Java Robot to select **Cook** on Cooking range ID **114**. The isolated server received ISAAC-decoded outgoing **opcode132, length6**, world(3362,4769), and paired synthetic **opcode253** acknowledgment for ID114. Original real socket receipt length **52 bytes**, SHA256 **`14bcb0fde2a93b8ce5b77726709281f4d8d98fcc88ca72829fcd47d4f424ed96`**; viewport nonblack **98.493%**; all child processes reaped by bounded runner. Screenshots, wire bytes, and source logs included privately. This establishes actual R299 *Linux GUI, menu interaction and synthetic protocol*, not live server cooking/inventory or Windows performance.

## Public GitHub changes and privacy

- `tools/recovery/r299/rebuild_r299_from_pinned.py`, **Git blob `27f1950bba7bef293f9cd8087e014fafe8858346`**: byte-identical to the actual twice-executed, SHA-enforced original-source R299 rebuild (source-safe, no original Java tree).
- `tests/java/r299/R299SceneMutationBoundsRegression.java`, **Git blob `ffd5c1f03be5e127908a3977a9e37f8be342d2e4`**: byte-identical to the Java regression that failed on original R298 and passed 136/136 on R299.
- `tests/python/r299/R299SourceSafetyRegression.py`, **Git blob `4bb04401d9a177823b9042fc973a91b08db7b5b1`**, **17/17** original source/pins/side-effects/source exclusion and negative-path tests locally and in Windows/Linux source-only GitHub Actions.
- Existing GitHub Actions source-safety matrix includes R299; **hosted CI does not have the owner-private Java/client/cache** and does not establish gameplay or native Windows GUI.

Private owner release, *not GitHub public*: **`SpawnPK_v309_R299_SCENE_MUTATION_BOUNDS_PRIVATE.zip`** size **2,968,394 bytes**, SHA256 **`715c991ad6749eedaccac8486fbb466b64653127d29fa424176f3db549419df4`**. Two deterministic byte-identical ZIP builds and independent CRC/SHA manifest and real socket/GUI/Java witness verification passed. It includes the private **compiled class-only** R299 JAR, scripts, tests and logs, two GUI screenshots/after-Cook images, local receipt/wire, and manifest; **no original complete game client, original cache, full original source tree, fonts, or credentials**.

## Acceptance boundary

**Native owner Windows R299 GUI NOT TESTED.** The R297 owner-native acceptance package still pins R295 and does not verify this newer compiled client. Nor does a synthetic localhost acknowledgment prove actual online original game-server cooking, item creation, authenticated login, inventory or sustained gameplay. Keep PR draft and current owner installation unchanged. Next material work: obtain owner-native R299 graphical acceptance or follow concrete new gameplay/scene defects supported by authentic failing regressions.

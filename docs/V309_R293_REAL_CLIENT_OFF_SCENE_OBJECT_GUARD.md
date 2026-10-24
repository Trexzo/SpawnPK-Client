# SpawnPK v309 R293 — real client crash fix: off-scene object menu actions

**2026-10-19. Real owner-private Java class change.** This milestone is not a Windows acceptance harness revision and does not overwrite/merge any installed client. Same draft PR #1142, same coordination issue #1117.

## Defect reproduced (actual R290 compiled client)

`Scene.getHashAtTile(int plane,int x,int y,int hash)` directly dereferences its `tiles[plane][x][y]` grid without bounds checking. Existing `Client.handleObjectClick` fetched this information **before** rejecting invalid scene/menu parameters. A stale or forged object menu carrying local tile X=-1 and Y=50 triggered a real `java.lang.ArrayIndexOutOfBoundsException: Index -1 out of bounds for length 104` from `rs.Scene.getHashAtTile`, propagated through `rs.Client.handleObjectClick`.

The actual old **R290 JAR**, not an invented stand-in, failed `R293OutOfBoundsRegression` with `R293_OFF_SCENE_X_CRASH`; error location and stack trace preserved in the owner-private evidence archive.

## Minimal source fix

Only `source/rs/Client.java` changes, immediately inside `private boolean handleObjectClick(int n,int n2,int n3,int n4)` and **before** its first `getHashAtTile` call:

```java
if (n == -1 || n2 < 0 || n2 >= 104 || n3 < 0 || n3 >= 104
        || planeLevel < 0 || planeLevel >= 4) {
    return false;
}
```

The **R290 scene-object-ID authority** check remains untouched. No new opcode, object definition, collision cache, route, server, network or GUI behavior was added. Only off-scene coordinates and invalid planes are refused before indexing.

## Verified on private real client

- Exact original owner-private R278 + R265 archives verified and 1,277 Java sources fully compiled with `javac --release 11` into **1,386 classes**.
- R293 reconstructed `Client.java` postimage SHA256 **`db1dfd4a4752fced78c2cb886bc50159eb8eeb8cc94d27c70b3d9e2ff1b1764c`**.
- Two independent private full recompilations **byte-identical JAR SHA256 `0d0eedae92efe709b2d6eb49b1fc4432db174a6e68a7f06fd4fc2736d0f6cee9`**.
- Compared to exact R290 JAR `f2f914f12196705fd7233ea022742157d13deb50be85289465ce26b0dde3cd4a`, **only `rs/Client.class` changed**; other **1,385 classes byte-identical**.
- Same real-class test red on unmodified R290, **green 71/71** on R293: invalid X/Y values -1, 104, 105, integer extremes, plane -1/4/extremes, empty in-bounds tiles, and all **seven** object-menu actions `1062, 900, 113, 872, 502, 62, 956` at off-scene tiles; no off-scene action packet transmitted.
- Independent unchanged R277 mixed-object packet codec test **38/38 PASS**.
- Source-only public safety regression **17/17 PASS** locally and in the original Windows Server 2022 / Ubuntu 24.04 GitHub Actions matrix.

## GitHub and reproducible owner-private deliverable

Public safe files:
- `tools/recovery/r293/rebuild_r293_from_pinned.py` — actual byte-identical tested/released script, Git blob SHA1 `7d767e702464ecf8474c138b3fb07ff8cde9f31c`; pins R278/R265 source/archive SHA, R290 authority patch, new R293 pre/post-image and resulting Java11 JAR SHA. Refuses unexpected original files, ambiguous source anchors and existing output.
- `tests/java/r293/R293OutOfBoundsRegression.java` — exact authentic red/green **71-case** Java test, Git blob SHA1 `adc583442025199b68a71030a87e014b66349e21`.
- `tests/python/r293/R293SourceSafetyRegression.py` — 17 source-only cases and no private/game code.
- Existing source-only Windows/Linux GitHub Actions workflow now runs the R293 Python safety suite; CI has no private class JAR and therefore **does not** claim to compile, GUI-launch or gameplay-test R293.

**Owner-private R293 release ZIP:** `SpawnPK_v309_R293_REAL_SCENE_BOUNDS_OWNER_PRIVATE.zip`, **2,380,177 bytes**, SHA256 **`c6ecd187ced1f6bae2858b846b5940a58d71a08f7031e938f4a2a15bb214f2cf`**. Two deterministic byte-identical release ZIP builds; independent manifest/member SHA256/CRC/binary provenance verification passed. Includes rebuilt compiled client-class JAR, authored rebuild/test scripts, expected preimage failure and verified postimage logs. **No original client executable, original game cache, original full recovered Java source tree, fonts, credentials, or private owner configuration**. Do not commit its private classes publicly.

Owner-private manual build is optional and uses the original pinned R278 and R265 archives, output must be a new path:

```powershell
python tools/recovery/r293/rebuild_r293_from_pinned.py --r278 ORIGINAL_R278.zip --r265 ORIGINAL_R265.zip --output NEW_PRIVATE_OUTPUT
```

## Acceptance boundaries

**Not tested in R293:** a fresh graphical Linux/Xvfb R293 session, native owner Windows R293 GUI, original online server-side gameplay/cooking effects, or installation on the user machine. Prior successful R290 graphical sessions remain R290-only evidence. **R292 native-Windows harness pins R290, not R293**; do not claim its results apply to the new compiled JAR. The next meaningful milestone is native Windows/GUI acceptance specifically for R293 or new evidence-backed client/gameplay fixes without weakening the source/authority protections. Keep PR #1142 draft; do not merge `main` on source-only CI success.

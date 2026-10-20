# SpawnPK v309 R309 — native Windows R308 acceptance adapter

This milestone updates the **owner-native test harness only**. No game class, cache, packet or source-built client JAR changed. The latest genuine client remains R308; PR #1142 remains draft.

## Scope and exact artifacts

- Public Python entry: `tools/windows/r309/R309-Windows-R308-Acceptance.py`
- Private owner-only ZIP (not in GitHub): `SpawnPK_v309_R308_SCENE_PLACEMENT_BOUNDS_PRIVATE.zip`
- Private ZIP SHA-256: `977645c2ed90c0936815e9da5ca609ee23480176088137f8d3e7ee3b88654d6c`
- ZIP member: `bin/R308_SOURCE_BUILT_CLASS_ONLY.jar`
- Compiled private JAR SHA-256: `501072d504a4e03a758f44aaa32f0990d3f1599662f6f6d2fa0d83a14e6fc314`

R309 reads the existing R297 readiness and GUI harness from this exact GitHub checkout, verifies their Git blob hashes (and the original GUI script's independent SHA-256), and adapts four pinned source literals in memory: private R308 ZIP name, its SHA-256, R308 JAR SHA-256 and four JAR member references. This reuses the original R286 guarded Windows GUI/Robot harness and its original-archive trust pins rather than duplicating launcher or isolation logic.

For compatibility, the original harness uses an internal `r295` parameter name; **its R309 value is the exact pinned R308 private package**, never an R295 client.

The original readiness gates are retained: Python/Pillow/Java, native interactive Windows, physical 1400×900 at 96 DPI, free loopback port 43594, safe fresh output path, exact private owner input hashes and original GUI source anchors. The native harness then checks the foreground Java window and drives the isolated localhost-only interaction. No user game folder is modified.

## Read-only inventory before running the owner GUI

From the same branch checkout, check all seven required owner-private files **without creating output or launching the client**:

```powershell
$Root = 'C:\path\to\SpawnPK-Client'
$Inputs = Join-Path $env:USERPROFILE 'Downloads'
$Entry = Join-Path $Root 'tools\windows\r309\R309-Windows-R308-Acceptance.py'
& py -3 $Entry --input-dir $Inputs --inventory
```

The single JSON result has one entry per required archive/JAR, with `MISSING`, `SHA256_MISMATCH`, `SYMLINK_REFUSED` or `SHA256_PASS`. This includes the seven exact R286/R308/R278/R265/assets/original/R230 dependencies. A nonzero exit means at least one input was not verified. It checks all seven rather than reporting only the first problem, shows filenames but not private absolute paths or measured hashes, and is safe to run repeatedly. **All seven passing still proves input checksums only, not ZIP overlay correctness, Windows readiness, graphical success or GPU correctness.**

Some earlier R308 packages have different archive SHA-256 values. Only the **specific pinned R308 private ZIP** above is accepted by this adapter; do not rename, force-accept or bypass a different archive checksum.

## Owner command

Use a checkout of the branch with R309 and all previously required owner-private archives already under Downloads. Start with the read-only preflight:

```powershell
$Root = 'C:\path\to\SpawnPK-Client'
$Inputs = Join-Path $env:USERPROFILE 'Downloads'
$Output = Join-Path $env:USERPROFILE 'Desktop\SpawnPK-R308-Native-Receipt'
& py -3 (Join-Path $Root 'tools\windows\r309\R309-Windows-R308-Acceptance.py') --input-dir $Inputs --output $Output
```

Only when the preflight reports `ready: true`, to actually run the guarded graphical test on Windows:

```powershell
& py -3 (Join-Path $Root 'tools\windows\r309\R309-Windows-R308-Acceptance.py') --input-dir $Inputs --output $Output --run-native-gui
```

Both commands reject an existing output path; preflight creates no output. The native run needs the original R286 private acceptance source ZIP and the other six pinned owner inputs. Never upload the owner ZIP, cache or screenshots publicly.

## Evidence boundaries

The public `tests/python/r309/R309SourceSafetyRegression.py` exercises source provenance, archive/JAR pinning, absence of owner inputs, source tampering, invalid method anchors, non-Windows refusal, and explicit GUI opt-in without launching the game.

Hosted source-only Windows/Linux CI cannot establish native owner gameplay or real GPU rendering. R308's independently reported 106,769 authentic JVM assertions and Linux Cooking GUI replay are pre-existing evidence, not new R309 test results. Native Windows R308 graphics (especially 50-tile draw radius), the production server and sustained gameplay remain unverified until an actual guarded Windows receipt exists. No merges or owner installation are implied.


Git-for-Windows CRLF checkout conversion is supported only by first canonicalizing CRLF to LF and then verifying the **same exact Git blob and SHA-256 pins**. Mixed/stray carriage returns and changed source bytes are refused.

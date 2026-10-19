# v309 R290 — source-built scene-hash/object-ID authority fix

**Implemented and independently verified 2026-10-19.** This is a real one-file owner-private client-source change; it is **not** another Windows harness change.

## Root cause and minimal production patch

The R274/R278 `Client.handleObjectClick(int n,int n2,int n3,int n4)` guard checked whether the scene entry for `n` still existed. But it did not check whether the outgoing menu object ID `n4` matched the object ID encoded in that scene hash. An object menu carrying the scene hash for **Cave Entrance ID 2** could send a packet with **Open chest ID 104** at the same scene tile, while the prior existence gate returned true.

The sole R290 production change to the recovered private `source/rs/Client.java` is inside the existing `handleObjectClick` authority check:

```diff
- if (n == -1 || n5 == -1) {
+ if (n == -1 || n5 == -1 || (n >>> 14 & 32767) != n4) {
```

R290 therefore rejects missing scene objects **and** mismatched transmitted IDs *before any of the five ordinary object option packet emissions* (options 1062, 900, 113, 872, 502). Existing R278 scene-presence checks remain; normal client menu handling is unchanged. No hardcoded new gameplay actions, cache definitions, bank bridging, asset modifications, network endpoint changes or protocol opcode changes.

## Actual private-source evidence (not synthetic-source-only)

All five exact owner archives were found in the user's private Library and SHA256 verified. R278 reconstructed base SHA-256 **319f893290473e6f144e04c89de6c7e48efaa03c8a10e6f2acd8a9e28c9aa959**, R290 post-patch source **b0a1ae721da4dc2e1b0bfb7ea6e434b2f8bc41126eb1bd1ec3f776c07f56772c**.

- **True red/green proof:** The original unchanged R278 compiled class JAR fails `R290ObjectIdAuthorityRegression` with `R290_FOREIGN_OBJECT_ID_ACCEPTED sceneId=2 sentId=104 option=1062`; the patched full-source-rebuilt client passes all **298/298** assertions, including twenty mismatched ID menu actions, twenty intact valid actions, multiple collision footprints, removal/re-insertion and movement.
- **Compilation:** all **1,277** real Java files compiled with `javac --release 11` into **1,386 classes**. Reproduced from original R265 + R278 inputs **twice**; resulting JARs byte-identical SHA256 **f2f914f12196705fd7233ea022742157d13deb50be85289465ce26b0dde3cd4a**.
- **Full compatibility:** 11 authentic real-client Java suites total **1,057/1,057** assertions, and independent strict packet suite **38/38**; **1,095/1,095** combined.
- **Actual Linux GUI/localhost:** two separate Xvfb Java GUI replays with original 10,772 cache assets; authentic region **13386 field1134**, Cook Cooking range ID **114** selected by AWT; output ISAAC-decoded opcode132 six-byte action at world(3362,4769), paired isolated server opcode253 reply; both sessions rendered >95% of their tested 3D viewport and exited 0. The two 52-byte independent server ciphertext receipts have SHA256 **5b5bb2254fffb4b2a0e96691779c0778902727d5577fc775d43bb64d2d9aaf07** and **2aba140aa539c69af3d26eb0a77cc1c61f91258156b31f2ef1e4a3d443542cdd**.

## Public GitHub, privacy and reproduction

- `tests/java/r290/R290ObjectIdAuthorityRegression.java` — source-safe, authentic client regression (Git blob **2e63389f494cfb02bc11f88bd69590fde97fb840**), proved **red on R278, green on R290**.
- `tools/recovery/r290/rebuild_r290_from_pinned.py` — SHA-pinned Java 11 full source build from **private owner R265 and R278 ZIPs** without committing or including either; refuses wrong hashes and existing output, compiles in disposable temp path (Git blob **eb7e296888cc116a15221c2a25a9521dbb00f68d**).
- `tests/python/r290/R290SourceSafetyRegression.py` — 14/14 source-only fail-closed tests, executable without original archives on Windows and Linux (Git blob **c2cc7c78089082b2a85f20922e1115ccd3994d68**).
- Existing GitHub Actions Windows/Linux safety matrix extended to execute R290 public-source negative cases; **does not claim Java/game runtime acceptance without private dependencies**.

The complete **owner-private** package `SpawnPK_v309_R290_OBJECT_ID_SCENE_AUTHORITY_PRIVATE.zip` is **3,566,285 bytes**, SHA256 **3bb467029ec552f7345a054dbed7ee8da2ef646bdfa2ce72707ce384b646f41c**, includes the compiled class-only JAR, private screenshots and localhost receipts, source-safe rebuild/test scripts, logs and manifest. Two deterministic release ZIP builds identical; independent archive verifier **145/145 PASS**. The private game binary and screenshots **were not committed to public GitHub**. No original client JAR/cache/font/full game-source tree in the package.

Rebuild (with the two exact original owner-private archives available):

```powershell
python tools/recovery/r290/rebuild_r290_from_pinned.py --r278 "ORIGINAL_R278.zip" --r265 "ORIGINAL_R265.zip" --output "NEW_PRIVATE_R290_FOLDER"
```

## Remaining acceptance boundary

**Native Windows R290 graphical acceptance NOT TESTED.** The previous R286/R288 Windows owner harness deliberately pins the previous R278 class JAR; it cannot be cited as a Windows pass of R290. Gameplay effect is validated only through authentic client/local synthetic-server protocols, *not* actual original game cooking/inventory/server effects, original authentication or sustained production runtime. Main remains unchanged; PR #1142 remains DRAFT; installed owner client untouched. Next substantial acceptance is an owner-native R290-compatible, SHA-locked GUI session (or new exact production-source gameplay defect evidence) without weakening original asset isolation.

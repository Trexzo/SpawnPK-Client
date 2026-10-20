# SpawnPK-Client R298 — actual read-only Scene query bounds, 12 real methods

**2026-10-20 — genuine recovered private Java client code changed; owner-local Windows GUI not tested.** All private original cache/assets/client binary remain outside public GitHub. The single ongoing PR #1142 stays DRAFT.

## Root cause, real R295 failure and scope

The R295 fix guarded `Scene.getHashAtTile`, but twelve separate **read-only object/scene query methods** still dereferenced `this.tiles[plane][x][y]` directly. Reflective invocation of the unmodified, actual R295 compiled class JAR with an invalid plane `-1` caused `ArrayIndexOutOfBoundsException: Index -1 out of bounds for length 4` in `rs.Scene.method1154`. This was reproduced with a real `Scene` instance before any R298 source modification.

The fix introduces one private, bounds-checked `safeQueryTile(int plane,int x,int y)` returning `null` when the requested scene tile or plane is unavailable. **Only twelve read-only methods** now use the helper:

`method1154`, `method1364`, `method1249`, `method2963`, `method2829`, `method2780`, `method2827`, `method2960`, `method1551`, `method2717`, `getInteractiveObject`, `method2918`.

The first eight return their existing absent sentinel **0**; the last four retain **null**. The indexes for methods whose argument order differs from their underlying plane/X/Y storage are mapped individually rather than assuming one common order. **No** scene placement/deletion, terrain, collision, network opcode, authentication, object definition or mutation code was changed. The previous R295 `getHashAtTile` -1 guard and R293/R290 `Client.class` menu authority remain intact.

## Actual owner-private class and regression evidence

- **Real red test on unmodified R295:** `R298_SCENE_QUERY_BOUNDARY_CRASH method=method1154 input=-1,50,50 cause=java.lang.ArrayIndexOutOfBoundsException`.
- **Green R298 rebuilt JAR:** 12 methods × (3 invalid argument positions × 4 extreme values + 4 valid empty tiles) = **192/192** real JVM assertions PASS. Invalid values include -1, 104, INT_MIN and INT_MAX; all methods return the original empty value, not a thrown exception.
- **Prior genuine class regressions** on R298 remain **R295SceneHashBoundsRegression 69/69 PASS** and **R293OutOfBoundsRegression 71/71 PASS**. Total **332 successful Java assertions**.
- **Two independent complete Java 11 builds** from the exact SHA256-pinned private R278/R265 owner source/compile dependencies: **1,277** original Java files compiled into **1,386** classes. Both JARs byte-for-byte identical SHA256 **`be86b334f9ddc471cc7353f4a9493587c8a8317ded4a3a6e538f0ba96c08fbc9`**.
- Exact R295 `Scene.java` postimage preimage SHA256 **`24790fc3aac8676df95c1cd0f830f26bc6ad749cc87435f47b9eb69c9c8ef813`**, R298 postimage **`1999066509802862ba8c7ba0e4d54cabdf0cf8da64aabbc370439eda287ceada`**. The reproducible source recipe rejects unexpected owner source, ambiguous method anchors, unexpected rebuilt SHA and existing target outputs.
- Class-by-class comparison with original R295 JAR: **only `rs/Scene.class` changed**, all other **1,385** classes byte-identical. No original game source, cache or fonts are in the private release ZIP.

## Authentic Linux/Xvfb GUI compatibility evidence — narrowly stated

A fresh R298 session used exact SHA256-pinned original archives, original source-owned R285 GUI harness retargeted to the exact R298 JAR and private release, and staged **10,772 authentic cache files**. The actual Java client rendered OSRS region **13386 / field1134** at **1400×900** with a populated viewport (**98.536%** nonblack pixels). The Java Robot selected **Cook** on Cooking range ID **114** and the independent localhost test server received an ISAAC-decoded outbound **opcode132 length6** interaction at **(3362,4769)**, followed by matched synthetic reply **opcode253** for object114. Actual 52-byte received ciphertext SHA256 **`2b3f9ae3c348407e0cea90af984440ab709c2217460960d886b93d8556b903a0`**. The inner GUI runner wrote `R285_BOUND_ISOLATED_OSRS_COOK_GUI_PASS`, `R285_SESSION_TERMINATED status=PASS`, and reaped client/mock server children.

**Do not promote inner GUI success to full wrapper acceptance.** The outer Python archive launcher did not report its final R298 success marker before its execution limit and therefore the full outer wrapper is **INCONCLUSIVE/NOT ACCEPTED**. No real native Windows R298 GUI was attempted, and R297's older Windows owner acceptance explicitly pins the **previous R295** JAR and cannot be used as R298 evidence. No original live game server, production login, actual item creation, inventory or economy effects tested.

## Public source-safe GitHub and owner-private release

- `tools/recovery/r298/rebuild_r298_from_pinned.py` — original source-pin checks from R295, plus source-hash-pinned R298 twelve-reader patch and strict full-build jar hash, byte-identical to the actual two build runs (Git blob SHA1 **`d09ff1cca2becf465a633a525e60f4bc93f7ffb8`**). No original game source/JAR cached in GitHub.
- `tests/python/r298/R298SourceSafetyRegression.py` — **14** source-only tests, no private inputs, run in the existing Win/Linux CI workflow. The authentic Java red/green regression `R298SceneObjectQueryBoundaryRegression.java` remains bundled with the owner-private ZIP along with both build logs.
- `docs/V309_R298_READ_ONLY_SCENE_QUERY_BOUNDS.md` — this authority and acceptance statement.

**Owner-private binary release**, not committed to public GitHub:

`SpawnPK_v309_R298_READ_ONLY_SCENE_QUERY_GUARDS_PRIVATE.zip` — **2,378,275 bytes**, SHA256 **`af18427ffa9dddbe0e03f375a08b55ca381788b30ccf035e586942fb75cf47f1`**. Twelve entries: source-built R298 class-only JAR, exact public-safe reproducible source recipe, authentic 192-case Java test, R295 failure trace, 332 green Java assertions, identical-build logs, binary class diff, README and SHA manifest. Two deterministic byte-identical ZIP builds; all members passed SHA256 and CRC checking. It is an owner-private deliverable and has **no original source tree, original complete game JAR, original cache, fonts or credentials**.

## Remaining gate

The 12 getter crash fixes and 332 JVM checks plus Linux synthetic-server GUI inner behavior are verified. **Full Linux outer wrapper completion and owner-native Win32 GUI for R298 are not yet verified.** R297 native owner launcher should not be silently reused for R298 without an explicit version-pinned update. PR #1142 remains DRAFT, no production owner installation and no merge to main.

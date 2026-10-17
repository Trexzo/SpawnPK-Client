# R266 — full Client opcode-81 integration and rendering gate

Continuation of [R265 draft PR #1142](https://github.com/Trexzo/SpawnPK-Client/pull/1142), with sole ownership per coordination issue #1117. **No production source change, no main merge.**

## Input integrity and isolated execution

The actual private R265 bundle from the owner's Library was materialized and SHA-256 verified:

- Full R265 ZIP: `9579556ab5b941bb2697955e56cf4b9d43b68787a652c580a702228554b28dbb` (25,129,777 bytes).
- Its previously compiled Java11-target production JAR: `dc42ce52380d51bbc6162589d66e7226e5c86541ab84869f710b38ceffd7a503`.
- Source count in ZIP: **1,277**. Cache helper in archive matches integrated R246: `030284641b3ce50a6e9324bb2bc96c83b8a2982db0ffd8fa41330b4139615ed2`.
- Only the new independently authored regression was compiled in this iteration, with `javac --release 11` against the pinned R265 JAR and pinned dependency JARs. It was executed in an isolated Linux Xvfb virtual display, with **no server socket** and no archive/cache writes.

## New direct decoder acceptance

`R266RealClientPlayerSyncRegression` invokes the **actual private `Client.method1850(int, Packet)`** via reflection. This is deeper than R265's standalone Packet/Player decoding, but **still not a GUI world-session replay**.

All **28 checks PASS**:

1. An actual new `Client` and local `Player` start without appearance.
2. The first 60-byte opcode-81 body passes the client's complete self movement/retained-player/additional-player/mask pipeline; `hasAppearance=true`, username `LocalTest`.
3. A valid subsequent three-byte no-mask player sync preserves the same local-player object and appearance.
4. A second 59-byte appearance frame changes the name to `LocalTwo` and keeps appearance.
5. Truncated appearance data is rejected (throws rather than silently reporting success).
6. Critically, `Player.method279(true)` on that parser-valid **all-zero equipment** fixture yields a `Model` with **0 vertices and 0 faces**, using initialized empty definition caches. This proves the previously accepted appearance bytes **cannot display a human character model**.

Expected output:

```
R266_CLIENT_81_FULL_DISPATCH_PASS checks=28 firstBytes=60 repeatBytes=3 secondBytes=59
R266_PLAYER_MESH_GATE_CONFIRMED vertices=0 faces=0 REAL_KIT_ASSETS_REQUIRED
```

The second result does **not** imply the actual game has no models: the isolated fixture deliberately contains no equipment or IdentityKit body components, and no authentic cache was mounted in this test.

## Full tree build limitation in this session

A new `javac` full-tree rebuild with the available **JDK 21** and `--release 11` failed to resolve colliding obfuscated Trove type/package names (for example `gnu.trove.f.b.cc`, where `gnu.trove.f` also exists as an interface). This produced compile errors, so **DO NOT claim a new 1,277-file full build pass**. The prior pinned R265 archive contains the independently documented Java11 compilation (1,277 source files, 1,386 classfiles, zero errors), but that is **historical R265 evidence**, not newly replicated evidence in R266. The new R266 test did compile and run with the actual R265 compiled classes.

## Next true runtime gate

Provide a properly **asset-backed** appearance body with real IdentityKit IDs from the authentic cache. Feed it over the persistent localhost 249 → 73 → 81 fixture and verify the resulting player has nonzero vertex and face counts; capture the real client GUI while the server remains open. Inspect terrain independently (region data, renderer buffers, framebuffer). Do not claim playable world, native Windows acceptance, genuine server protocol parity or hardware power-loss safety until separately tested.

No proprietary private client source is committed in this PR. Public evidence contains only independently authored regression and documentation. Retain this PR as **DRAFT**.

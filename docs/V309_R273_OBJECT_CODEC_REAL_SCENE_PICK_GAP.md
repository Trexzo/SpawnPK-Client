# v309 R273 — authentic world-object protocol audit; GUI interaction unresolved

**Sole-owner integration, 2026-10-18.** This is a **source-backed offline milestone**, **not** a verified live GUI object click. Production client source unchanged. No original-derived Java, cache data, or runtime JAR committed. PR #1142 remains DRAFT.

## Actual R265 source-built client + user cache results

Genuine owner `.spawnpk (4).zip` object definition **ID 104**, `Open chest`, real model **1226** and action names **Search** and **Shut**. The actual compiled `ObjectDefinition`, `Scene.getHashAtTile`, `Client.handleMenuAction`, `Client.method2310`, `Packet` and ISAAC paths were invoked, not substitutes.

- Packed object scene hash **1075452082**, local (50,49), type 10.
- Actual menu option **502 / Search** produced opcode **98** approach + opcode **132** object action, total **16 source-encoded bytes**: `2e07010c0101800c00b8020c00680c01`. Expected world (3202,3201), ID 104.
- Actual option **900 / Shut** produced opcode **98** approach + opcode **252**, total **16 bytes**: `2e07010c0101800c0030e800810c0c02`.
- Actual item-on-object with a valid scene hash emitted opcode **192**.
- Actual inbound object-spawn subpacket **151** in top-level 60 placed a model/shape-10 update for ID104 at (50,49) into the client's pending scene queue. **Queue acceptance is not proof of on-screen rendering.**

### Confirmed stale-scene-object lookup issue

When the caller supplied a **non-sentinel positive packed object hash** but `Scene.getHashAtTile` returned **-1** (object actually missing), the real compiled client's item-on-object branch still emitted **opcode 192**. The implementation's `handleObjectClick` examines the *supplied* `n == -1`, not the missing *lookup* result `n5 == -1`. This is reproduced from real client classes; it is **not** yet a production fix or basis for claiming all interaction branches safe. A correct fix must distinguish missing objects from supported clicks without changing legitimate object-option behavior, and must compile and pass further regression tests.

## Actual verified regressions

- **39/39** Java menu, scene lookup, object packet / missing-object test checks.
- **12/12** Java inbound object-spawn decode and queue checks.
- **33/33** separately implemented Python ISAAC framing, coordinates, and truncated/malformed input checks.
- Complete disposable isolated Linux runner: **84/84 PASS**.
- Independently run source-free ZIP evidence validator: **62/62 PASS**.
- Original private baseline: R265 complete source archive SHA256 `9579556ab5b941bb2697955e56cf4b9d43b68787a652c580a702228554b28dbb`; owner cache ZIP SHA256 `8e15964f44b62a22d2c05f0ae2f63d45ddad42016c721e586cf55a82d35da565`.
- One evidence ZIP `SpawnPK_v309_R273_AUTHENTIC_OBJECT_CODEC_AND_SCENE_GAP_EVIDENCE.zip` **SHA256 `a1bffc210b56d9f000ec81326d39986f937a220546c709d60c67446975952205`**, 15 entries, CRC verified; Java/ISAAC test sources, Linux and unexecuted Windows scripts, logs and **failed object-picking GUI evidence**. No game JAR, original source or private cache bundled.

## GUI limitation and full-client build

A source-built Linux Xvfb graphical test reached a populated scene (>99.7% nonblack viewport), sent an authentic object-spawn subpacket, then made an AWT right-click at the estimated chest location. The *real menu displayed only Walk here / Cancel*; no selectable chest or GUI-originated opcode132 was confirmed. A longer exploration timed out, followed by a shorter diagnostic screenshot replay; neither constitutes accepted GUI interaction. More work is required to establish pickable cached geometry at a correctly projected tile and verify on-screen object selection and wire receipt.

A fresh full 1277-source `javac --release 11` attempt on **host JDK21** hit existing obfuscated Trove type collisions. R273's passing Java tests use the **previously source-built R265 Java11-target compiled client**, not a successful newly compiled R273 production JAR. Windows runner included but unexecuted.

**Next R274:** isolate object scene promotion and mouse-pick projection; enforce a real rendered/pickable object gate before click. Test independent server receipt of actual GUI opcode132 and send a clearly synthetic reply; fix missing-object lookup only with verified compilation and regression. Keep all historic PRs and #1142 DRAFT; no merge to main.

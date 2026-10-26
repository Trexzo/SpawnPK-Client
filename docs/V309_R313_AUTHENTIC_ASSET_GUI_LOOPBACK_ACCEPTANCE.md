# R313 — authentic cache-backed full-source v309 GUI and isolated local world acceptance

**26 October 2026.** [Draft PR #1143](https://github.com/Trexzo/SpawnPK-Client/pull/1143), coordinated in [issue #1117](https://github.com/Trexzo/SpawnPK-Client/issues/1117).

## Genuine asset inputs recovered

For the first time after R312, the original owner-v309 cache bundle and original client resources were independently recovered and verified against the historical SHA-pinned R285 fixture:

| Owner-private input | Exact SHA-256 |
|---|---|
| Original 10,772-file cache ZIP (`.spawnpk (4).zip`) | `8e15964f44b62a22d2c05f0ae2f63d45ddad42016c721e586cf55a82d35da565` |
| Original v309 resource client JAR | `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38` |
| Original R265 recovered-source integration ZIP | `9579556ab5b941bb2697955e56cf4b9d43b68787a652c580a702228554b28dbb` |
| Original R230 asset mappings ZIP | `5c21e5c643de759da80c4d18ebb6a49c84968d47a979caa33f7d4ad2170a7125` |
| Rebuilt R311/R312/R313 full-source class-only client | `b551c58e7e07154f1a5b27e153db9df803bbbca820cc8ee133e8b515aba72721` |

The asset ZIP contains **10,772 `.spawnpk/` files / 209,747,201 uncompressed bytes**. It also contains unrelated `.spawnpk-data/` files, which were **not staged or used**. The historical reviewed R285 `stage_owner_inputs.py` extracted only `.spawnpk/` into a separate test home, generated a **resources-only** classpath JAR from the original client JAR, and staged the required private Java dependencies. The actual running game implementation was the recovered-source rebuilt R311 class-only JAR, **not** the original client JAR.

## Actual full-client GUI/world evidence

Real Java client startup and AWT GUI under isolated **Linux/Xvfb 1400×900**, with explicit `spk.offlineProbe=true`, server host **127.0.0.1:43594**, dummy test identity and no user accounts or production servers. Historical local synthetic ISAAC protocol server and RobotLogin/CookRobotR285 UI fixtures were reused unchanged, except that the client JAR was replaced and its SHA pin updated.

**Two completed independent replays**:

1. First bounded replay finished **PASS** at approximately **28.05 seconds**; client GUI loaded, original region **13386** from bank **field1134** appeared, textured terrain/objects/local actor/minimap rendered (crop nonblack ratio **0.98520**), and actual mouse interaction generated a real ISAAC-decoded opcode **132**, 6-byte Cook object action for **object ID 114**, world tile **(3362,4769)**. The test server returned opcode **253**; the synthetic action had a 52-byte wire receipt with matching SHA-256.
2. An independent fresh-staged replay finished **PASS** at approximately **30.32 seconds**, capturing an additional late world screenshot with both Java client and server processes still alive at the 30.3-second check (crop nonblack ratio **0.98534**), with the same object/action/reply identity and a separately hashed 52-byte wire witness. All launched child processes were terminated at the end.

An exploratory **43-second** hold exceeded the local test tool's execution window and was NOT accepted. The current evidence establishes at most 30.3 seconds of observed local runtime, not sustained multi-minute gameplay.

## Cumulative private delivery

`SpawnPK-v309-R313-Full-Recovered-Source-Private.zip`, **22,928,704 bytes**, SHA-256 **`fb078ae1911af9c774faeb1ec165dd881c3ec65bf0af0dcb697409f92e92df9a`**.

The private archive contains all **1,277 recovered original-derived Java source files**, private dependencies, the unchanged **1,386-class JAR**, prior R308–R312 regression and offline-render harnesses, a new explicit input-SHA-locked `tools/run_r313_asset_gui.py` with historical fixture scripts, and privately held local GUI evidence/screenshots. The original 203 MB cache ZIP, original v309 resource JAR, source input archives, account data and separate `.spawnpk-data` files are **not included**. The output archive was checked for ZIP validity and cleanly extracted.

**Clean extraction acceptance:**
- Original inherited R312 real compiled-client offline suite **2,703 / 2,703 assertions PASS**.
- Fresh `javac --release 11` build of **1,277 Java files → 1,386 class files**, reproduced exact unchanged production JAR SHA-256 `b551c58e7e07154f1a5b27e153db9df803bbbca820cc8ee133e8b515aba72721`.
- The new packaged GUI runner reached and wrote a **PASS result and 30.32-second verified local-world receipt**, although the outer command's stdout pipe was cut immediately afterward by the tool execution window; its top-level exit code is **not certified** by that run. The two earlier GUI replays exited successfully and remain the primary accepted evidence.

## Strict limits / release gate

R313 makes **zero production game-source changes** from R311. This is authentic asset-backed **local GUI + local synthetic protocol acceptance**, not authenticated public SpawnPK gameplay, full feature parity, owner-native Windows startup/GPU/NTFS certification, multi-minute stability, or original v311 bytecode parity. Preserve current draft/unmerged status. Keep all owner-private original and recovered assets off public GitHub; only this redacted source-safe verification record is committed here.

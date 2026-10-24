# SpawnPK v309 R273 — genuine cached world-object actions and missing-hash finding

**Status:** 84/84 offline direct compiled-client and independent packet-decoder assertions PASS. The graphical world-object click was **not** accepted. No production Java modified, no main merge. Sole active SpawnPK-Client integration PR #1142.

## Actual source-backed Java 11-target behavior

Used SHA-256-pinned original R265 source-built JAR `dc42ce52380d51bbc6162589d66e7226e5c86541ab84869f710b38ceffd7a503` and exact owner asset snapshot `.spawnpk (4).zip` SHA256 `8e15964f44b62a22d2c05f0ae2f63d45ddad42016c721e586cf55a82d35da565`. Fresh temporary staging of authentic cache verified both input ZIP hashes.

Cached object **104: Open chest**, model **1226**, menu options **Search** and **Shut**. Actual `ObjectDefinition`, `Scene.getHashAtTile`, `Client.handleMenuAction`, `Client.method3573`, `Packet` and ISAAC used with a synthesized (but actual Scene-compatible) type-10 scene hash at local tile (50,49), region base 3152/3152.

- **Search** action 502 → authentic **approach packet 98**, followed by **object packet 132**. Actual 16-byte client output (ISAAC seed [13,22,37,41]) `2e07010c0101800c00b8020c00680c01`.
- **Shut** action 900 → authentic **approach packet 98**, followed by **object packet 252**. Actual 16-byte client output `2e07010c0101800c0030e800810c0c02`.
- Both action packets independently decode object ID 104 and world tile **(3202,3201)**, preserving their distinct byte-order transformations.
- The item-on-object action on a matching scene hash sends opcode **192**. The special sentinel hash `-1` blocks it.
- **Reproduced defect:** `Scene.getHashAtTile` can return **-1** for a mismatched *non-sentinel* object hash, yet the actual item-on-object branch still sends opcode **192**. In the R265 source, `handleObjectClick` checks the input `n == -1` rather than the failed lookup `n5 == -1`. Unconditional object-option branches also need review. **This is NOT safely guarded in the baseline**; no speculative patch promoted without a full build.
- Actual incoming `Client.method2310` parsed the four-byte object subpacket **151** and queued object 104, shape 10, at local tile (50,49). This establishes inbound decode/queue semantics, **not a rendered/selectable object**.

Tests: actual Java action/scene regression **39/39**, actual Java incoming 151 regression **12/12**, independently authored Python ISAAC object-wire framing/truncation **33/33** = **84/84 PASS**. One checksum-guarded Linux runner reproduced all 84 from a clean, disposable home. Windows PowerShell runner supplied but unexecuted.

## Separate GUI experiment: NOT ACCEPTED

The source-built R265 diagnostic GUI successfully logged in to dummy **127.0.0.1-only** listener, rendered a populated 3D viewport (measured **99.75% nonblack**), and was sent top-level opcode 60 containing object subpacket 151. Actual AWT right-click at the presumed chest tile produced only **Walk here / Cancel**, not the authentic chest context menu. A longer exploratory replay timed out; the shortened rerun captured the negative menu result. No genuine GUI-selected 132 packet or server object response was observed. Do **not** describe this as a successful GUI object interaction.

An attempted fresh full **1,277-Java** compile under current **JDK21** with `javac --release 11` failed early on pre-existing obfuscated Trove dependencies (for example `gnu.trove.f.b.cc`), before class output. R273 instead executes the authentic previously compiled R265 Java11-target JAR; no new complete full-source build is claimed.

## Evidence archive

`SpawnPK_v309_R273_AUTHENTIC_OBJECT_CODEC_AND_SCENE_GAP_EVIDENCE.zip`, SHA256 **`a1bffc210b56d9f000ec81326d39986f937a220546c709d60c67446975952205`**, 483,607 bytes; two builds byte-identical; CRC and SHA-manifest PASS; 62 independent archive assertions PASS. Contains two standalone real compiled-client Java regressions, a Python wire decoder, SHA-guarded Linux/untested PowerShell runners, private input extractor, logs, negative GUI screenshots, and README. Original game source/JARs/assets/private data NOT included.

**Next R274 acceptance:** locate real spawn geometry/scene-picking position, verify true on-screen **Search Open chest** menu and actual client-generated opcode132 receipt at localhost, then validate server-framed object response. Separately design/test source hardening for absent scene hashes with an actual supported full-source Java toolchain. Keep draft, no automatic merge to main.

# v309 R276 — Three-object scene/collision lifecycle and extended localhost GUI

**Verified 2026-10-18.** Sole client owner continuing R275 and private R274 source-built Java11-target class-only client with the stale-scene-object guard. Production code unchanged this batch. **DRAFT; do not merge main.**

## Real compiled-client multi-object test: 83/83 PASS

An independently authored Java regression runs actual R274-compiled \`Client.method2310\` (incoming object 151/101), \`Client.method1808\` (pending queue), original authentic cached Open chest definition ID104, real OSRS model1226 (152 vertices, 286 faces), \`Scene\`, \`CollisionMap\`, and \`Client.handleMenuAction\`.

- Spawns **three adjacent authentic chests** at local tiles (50,49), (51,49), (50,50) in the same scene. Before tick, all three are pending; after tick, each has its own resolvable packed scene hash and individual collision flag.
- Removes only middle tile (51,49), verifying its collision flag clears while both neighboring objects and their collision masks remain unchanged.
- Proves the private R274 guard rejects a positive **stale scene hash** for item-on-object action62 without emitting opcode192; restores middle chest, validates proper geometry/collision and verifies valid item-on-object is again permitted.
- Removes remaining chests in reverse order, checks all three collision tiles cleared, verifies duplicate removal is idempotent, and confirms an unrelated tile remains untouched.
- **83/83 real client Java assertions PASS**.

A separate strict source-derived opcode60 with nested 151/101 packet-framing/malformed-input regression passed **32/32**. Hash-pinned clean extraction from original R274 ZIP, R265 ZIP and owner's \`.spawnpk (4).zip\` reran both suites independently **115/115 PASS**, compiling the standalone test under \`javac --release 11\`. Earlier R274 full rebuilt-client 316/316 suite is **historical evidence only**, not rerun in R276.

## Real graphical test — two independent local replays

The original source-built client in 1400×900 Linux/Xvfb received **one real opcode60 packet with three nested chest151 spawns** after map-ready121; the actual inbound client packet capture includes the 17-byte payload:
\`30 D0 97 A1 68 00 58 97 B1 68 00 58 97 A2 68 00 58\`.

One authentic AWT chest right-click/selection in each replay produced client-originated **opcode132**, independently ISAAC-framed by the isolated \`127.0.0.1:43594\` mock listener. Both packets target cached object104, world tile (3202,3201); mock server returned opcode253 synthetic \`Chest: The lid creaks open.\` chat. Wire offsets **43** and **42**, with distinct per-session receipt hashes.

- **Replay 1:** a successful real chest interaction and **70 additional seconds** with stable rendered viewport; screenshots at interaction+0/+30/+60, actual client packet capture confirms **33** 3-byte incoming player-sync heartbeats.
- **Replay 2:** separate staged home, successful independent chest interaction and **32 additional seconds** stable viewport; screenshots at +0/+10/+20/+30, client packet capture confirms **18** heartbeats.
- Pixel-decompressed final screenshots independently show **99.57%** and **99.58%** nonblack pixels in the real 504×335 3D view.
- An intermediate second-run attempt was excluded from success totals because the harness deleted its own already-written action receipt. The client capture proved the packet had arrived; correcting receipt deletion timing yielded a new successful independent replay.

**Evidence limit:** The server receipt records the initial interaction ~7 seconds after post-login; the 70/32-second continuation is supported separately by captured incoming heartbeat frames, still-running GUI process checks and screenshot gates. Do not label these as full long-running server receipt files. Adjacent chests have overlapping screen positions; only **one particular visible chest action per replay** was tested. Synthetic chat is not actual loot/inventory logic or genuine production authentication.

## Source-free package, integrity and reproducibility

\`SpawnPK_v309_R276_MULTIOBJECT_COLLISION_EXTENDED_GUI_EVIDENCE.zip\`  
SHA256 **\`b3c0c3f6bf92a99f7ac719cca8ba85dc78e23b7083688cf27eae51c9626c44ec\`**, **2,705,467 bytes**, **48 ZIP entries** including manifest. All archive CRC, entry sizes and SHA256 verified; two independent deterministic builds byte-identical. Independent standard-library validator: **144/144 checks PASS**, including two screenshots actually decompressed/inspected (not only trusting runner logs). Private original client JAR/classes/source/asset cache and real account credentials **not included**.

The ZIP contains actual standalone Java 83-check test, Python 32-check framing test, SHA-guarded disposable Linux and prepared-but-unexecuted PowerShell runners, both genuine GUI captures/screenshots and the locally executed synthetic-server/Robot harness. Exact clean offline command:

\`\`\`bash
bash scripts/run_r276_linux.sh R274_PRIVATE.zip R265_PRIVATE.zip '.spawnpk (4).zip'
\`\`\`

The graphical reproduction harness documents the original Linux workspace path assumptions; full GUI native Windows acceptance remains **unverified**.

## Next R277

Keep one active PR #1142 DRAFT. Next focus on **different object IDs/models and collision footprints**, collision-aware click/path failure cases, and a longer client-driven movement+NPC/object mixed scenario. Native Windows acceptance and original gameplay-server logic remain separate. No production source changes, no main merge.

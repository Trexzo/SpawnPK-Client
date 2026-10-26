# v309 R267 — real cache-backed IdentityKit player model

**Status: 75/75 offline checks PASS (Linux/Xvfb).** This is a continued regression on the integrated R265 client baseline, not a gameplay release.

## Inputs (strictly pinned)

- Original user's private R265 ZIP: SHA256 \`9579556ab5b941bb2697955e56cf4b9d43b68787a652c580a702228554b28dbb\`
- Original user's October 17 .spawnpk (4).zip: SHA256 \`8e15964f44b62a22d2c05f0ae2f63d45ddad42016c721e586cf55a82d35da565\`
- R265 **actual production built** Java11-target JAR: SHA256 \`dc42ce52380d51bbc6162589d66e7226e5c86541ab84869f710b38ceffd7a503\`

## New implementation and verified result

The public test \`tests/java/r267/R267AuthenticKitRegression.java\` independently reads the actual \`.spawnpk\` cache archive. It validates original \`main_file_cache.dat\` and 6-byte \`idx0\`/\`idx1\` entries, follows 520-byte cache sectors (file ID, sequence, index checks), obtains the original config archive (index 0 file 2) and calls real \`IdentityKit.load\`. The archive contains 84 actual identity kits.

Seven selectable kits (IDs 0, 10, 18, 26, 33, 36, 42) reference **actual models** (230, 249, 292, 151, 176, 254, 181), loaded from real index 1 sectors. The original GZIP model data is decoded by the real \`Model.method1700\` / \`Model.method3293\`. **All seven have nonzero vertices and faces.** No models were invented.

A synthetic *localhost-only/offline* 66-byte opcode-81 appearance packet (mask 0x10), populated with genuine kits, is passed through **real \`Client.method1850\`**. The real \`Player.method279(true)\` now returns a **264-vertex, 472-face mesh**. Follow-on normal 3-byte no-mask sync retains the mesh. A subsequent full appearance replacement retains mesh/updates name. A deliberately truncated masked frame is rejected. 75/75 assertions passed both a direct run and independent SHA-pinned Linux launcher replay. These tests use actual compiled R265 classes, not fabricated client implementation.

## Acceptance boundary

**Player-model availability is verified, not on-screen player drawing.** The historical R264 isolated GUI still showed black terrain and no actor; R267 did not run a new full graphics session. Sustained gameplay, terrain visibility, native Windows, real authentication, original v309 bytecode parity, and power-loss durability remain unverified. Halloween cache assets and R265 source snapshot are from different points in time: passing this model test does not establish whole-client compatibility.

Windows PowerShell and Linux runners, manifest and logs are distributed in the private-source-free R267 evidence ZIP. Private original-derived Java, assets and dependencies are intentionally **not** published on GitHub.

Keep #1142 as DRAFT, maintain sole ownership per issue #1117, and do not merge stacked historical donor PRs on this result.
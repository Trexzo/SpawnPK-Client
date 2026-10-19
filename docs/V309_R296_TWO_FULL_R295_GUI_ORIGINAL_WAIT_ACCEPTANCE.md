# SpawnPK v309 R296 — genuine full-wrapper R295 Cook replay, previous timeout resolved

**19 October 2026.** Two newly staged **actual R295 client** graphical replays have now completed successfully through the original, unmodified `xvfb-run` wait and **the entire outer archive wrapper**, returning genuine process exit code **0** twice. The previous R295 outer-wrapper TIMEOUT reports are retained as historical evidence but no longer describe the behavior of these newer complete Linux runs.

**No production Java code/class changes.** R295 remains the current source-built client; all private owner inputs and caches stay outside public GitHub. Existing PR #1142 remains DRAFT; no merge or installation.

## Root-cause investigation and outcome

Previously, two fresh R295 GUI runs reached `R285_BOUND_ISOLATED_OSRS_COOK_GUI_PASS` and `R285_SESSION_TERMINATED status=PASS` but **their outer Python wrapper failed to produce a final completion status within the execution window**. R295 reports correctly treated those tests as *inner-only* and did not invent an outer PASS.

R296 separately reproduced the inner test in a supervised `xvfb-run` process and observed clean termination (exit 0, roughly 29s). A complete archive-to-GUI run under an external supervisor then returned exit 0; a second and third freshly staged run were performed with **the original R285 `proc.wait(timeout=85)` logic, without any forced `killpg` or fabricated `return_code=0` success**. Both **original-wait** runs returned 0 at the Python outermost process level. The earlier Python tool execution limit is a plausible explanation for the apparent incomplete outer wrapper; however, the evidence proves repeatable successful completion, not that every prior interruption's cause is conclusively established.

The source-safe `tools/gui/r296/R296ReplayOriginalWait.py` reproduces the original R285 harness by verifying exact SHA256 values of all seven private input archives and the three original R285 source members, applying only uniquely anchored R278→R295 JAR-selection overlays, and preserving the original bounded process wait. It refuses existing output paths and does not access the public/live game server. Git blob **`68dfb944602c52eb2f9059238cc0eaad85698a28`** is **byte-identical** to the actual driver that yielded both complete original-wait results.

## Two full fresh Linux/Xvfb R295 graphical accepts

| Verification | Fresh run A | Fresh run B |
| --- | --- | --- |
| Original source wait/outermost process | **Exit 0** | **Exit 0** |
| Fresh authentic cache staging | 10,772 files | 10,772 files |
| Exact client JAR SHA256 | `f5b6f4b6...` | `f5b6f4b6...` |
| Authenticated synthetic local session | PASS | PASS |
| Region/definition bank | 13386 / field1134 | 13386 / field1134 |
| AWT Cook Cooking range | ID 114 | ID 114 |
| Actual decoded outbound socket action | opcode 132 / 6 bytes / tile 3362,4769 | opcode 132 / 6 bytes / tile 3362,4769 |
| Isolated paired reply | opcode 253 / ID 114 | opcode 253 / ID 114 |
| Actual 52-byte received-wire SHA256 | `d8f99a9db8ef1472caf983c4469b5c5028a787f0d6622f5e99958fc5ba53becb` | `fc7ac51a01ee98b9d26bcb15906b1254648887ad4ff7cb83d895920b6ad998ac` |

The full R295 class-only JAR has SHA256 **`f5b6f4b6ea3e5e8fc49e1cbe61197647ed7c1e238a49d935c77882cb40da2e35`**. Both runs created unique isolated test homes from the seven exact source/asset packages, displayed real 1400×900 screenshots with a greater-than-95%-populated 3D viewport, and completed the original source-driven Robot action and localhost-protocol checks. Different ciphertext and world screenshots show two distinct sessions.

The final original source wrapper wrote `R295_R295_FRESH_GUI_COOK_PASS` and the outer driver wrote `R295_R295_SOURCE_BUILT_LINUX_GUI_REPLAY_PASS` in both runs, with separate `*_EXIT=0` supervisor status files. The *one* R295 process-group-reaper run also returned 0, but it is deliberately **not counted** toward the stronger two-run original-wait result.

## Private release and independent proof

Owner-private, **not committed to GitHub**: `SpawnPK_v309_R296_TWO_FULL_R295_GUI_REPLAYS_PRIVATE.zip`, **1,631,680 bytes**, SHA256 **`cb8688a5f02c3ee1e9e2c8f2418ee8add86ad5075a2dc4fb9c71f911afc58034`**. Two byte-identical deterministic builds, 36 ZIP entries, original PNG screenshots, socket bytes, receipts, source-safe scripts, independent process-exit evidence, timelines and negative input/output tests.

Independent public-safe verifier `tests/python/r296/R296EvidenceVerifier.py` is byte-identical to the actual **220/220 real-private-evidence checks**, blob SHA1 **`e50bf7e58e2c2f514ac2202d2994a64aa8fa06d2`**. It checks the original unmodified wait policy, each process exit, no fake forced-reaping marker, exact Cook socket/ack, original region loading and scene render, PNG dimensions/viewport coverage, SHA/CRC, client/server cleanup, screenshot/wire independence and negative hash/output refusals. No client JAR/class, original caches, full owner source, fonts or credentials appear inside the evidence ZIP. It contains gameplay screenshots and remains private.

`tests/python/r296/R296SourceSafetyRegression.py` adds **20 public source-only regression tests**, including strict archive SHA pins, unique overlays, refusal of input tampering/overwrite, and proof that the original bounded wait was *not* replaced with a forced success. Its Git blob **`6bfd1288fa0cedf56901d1b7ff68c2adb754d49e`** matches the executed suite. Windows Server 2022 and Ubuntu 24.04 CI run the 20 source-only tests; hosted CI contains **no private original client or cache** and must not be described as native-gameplay acceptance.

## Remaining boundaries

- **Linux full-outer GUI wrapper with R295: 2/2 passed**.
- **Actual original online game server/cooking effects, inventory changes, authenticated live sessions, sustained production gameplay: not tested**. This test uses an isolated local synthetic server and packet acknowledgment.
- **Native Windows R295 GUI: NOT TESTED**. Older owner Windows R292 acceptance pins R290; it cannot be cited as R295 proof.
- PR #1142 remains DRAFT/open. No merge to `main`, no owner-client installation and no proprietary binaries in public GitHub.

The next substantial milestone should be *native owner Windows R295 graphical acceptance* with immutable pinned archives or a new real client-source regression that directly extends gameplay rather than adding unnecessary preflight layers.

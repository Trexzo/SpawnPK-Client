# R241 Lane A integration gate — cache R233/R234 and runtime acceptance

## Verified upstream baseline (not rerun in R241)
Canonical Lane A draft PR #1084 is at R240 (head b984a1ffc4991f96f72c7dffcc8393741e9a7634). R240 reports 1,277 Java 11 sources, 1,386 compiled classes, zero compiler errors, 13 passing cache regressions. Private canonical source and production class-only JAR are not committed in this public branch. Earlier R235 protocol test verified initial 0e1d, challenge response, opcode 16 with 105-byte login payload, and rejection code 3; it **did not** establish valid login/world entry and was on an older binary.

## Strict sequential cache donor contract (Lane B owns implementation)
1. R240 current `src/rs/cache/updater/assets/CacheUpdateTransaction.java` SHA-256 must equal `a7f823d22ac3b0a97c97d5fba27193d2ae4a39fd1ce9b02a9127edb1bf7a8e79`.
2. Integrate only R233 exact donor from Lane B issue #1117 / draft PR #1126; expected SHA-256 `5bd41aa1442642ce9b3ddc7a914cf0a98be98b6f3a85e763e7281b3dfe86aff6`. R233 verifies promoted live content before deleting prior backup.
3. Then integrate only R234 exact donor from issue #1117 / draft PR #1127; required preimage is R233 above, expected SHA-256 `bc08aff2ddd3948f5ea8c248100234a39ee03cafd66b24e27b48c85e91aa2cad`. R234 versions new journals V2 and rejects missing required install witness after PREPARING; old V1 journals remain V1.
4. Abort if **any** preimage, donor, branch head, or 1,276 non-target Java files disagree. Create .bak and reversible ZIP before overlay. Never transplant entire Lane B source tree.
5. Recompile the **actual merged** 1,277-source Java 11 tree with original allowed dependencies; run all inherited Lane A cache suites plus R233 (promoted witness) and R234 (V2 / genuine V1 legacy) tests. Preserve full commands/logs, source/JAR SHA256s and changed-file inventory. Donor's own 20/21-suite passes do not prove merged Lane A acceptance.

## Client runtime matrix on the *new* merged JAR
- [ ] Isolated authentic-asset bootstrap: full login GUI; no unhandled Java startup exception; capture JAR hash and screenshot.
- [ ] Local listener strictly 127.0.0.1:43594; verify first client bytes `0e1d`, challenge framing, login opcode 16 and declared-versus-received payload length. Use disposable credentials and redacted logs; do not infer 105 bytes must remain invariant after changes.
- [ ] Server rejection code 3 produces expected invalid-credential UI.
- [ ] Separately implement/verify **successful authenticated** protocol in an isolated, approved localhost emulator; prove game state entry with server/client logs, not merely TCP success.
- [ ] Repeat GUI, loopback and offline cache tests on real Windows using SHA-pinned JAR/assets. Native hardware power-cut and real gameplay remain separate acceptance gates.

## Distribution / coordination
Private original-derived Java source and assets remain in private handoff bundles unless redistribution rights are explicitly resolved. Draft PR #1084 remains draft. Chat B continues cache-owner R233/R234 work; Lane A owns only canonical merge, build and client runtime validation. **This R241 document is a gate/coordination artifact, not a claim that R233/R234 or any runtime test has been executed.**

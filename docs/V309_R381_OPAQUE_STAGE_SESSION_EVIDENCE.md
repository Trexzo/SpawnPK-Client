# R381 — opaque save-attempt evidence (private v309 source candidate)

**Repository:** Trexzo/SpawnPK-Client. **Base:** R380 draft PR #1175. Keep **DRAFT / UNMERGED**; the Source-M1 private-source release gate remains closed.

## Bounded source change

Exactly one of 1,277 recovered Java files changed: `rs/gui/loadouts/io/LoadoutStore.java`. Each new folder save stages bytes using an opaque random 32-hex attempt token, alongside the existing SHA-derived folder lock key. Read-only diagnostics extract this session token from strictly validated stage filenames. Existing R380 and older stage filenames remain readable and session-unknown, and R380's lock correlation accepts the new format.

**A session filename is unauthenticated.** It does not identify a process or establish ownership of stage bytes; any process with directory write access could forge one. A free or busy cooperative lock, old timestamp or stable filename is not proof of abandonment. There is **no automatic cleanup, stage payload reading or deletion**.

## Verified offline evidence

- R380 private source SHA-256: `2ff9eb506ac001cb0c63f0dc1cbaf45fd322af33bb4191146afcdc88c1b8b3a6`.
- R381 private source SHA-256: `c5350e964219a36f79584576ce60693d49eec0e5b0ee2138cfcab258aa47bca7`; exact one-file diff and all source hashes checked.
- 33 new source-backed assertions pass; R380's 24 folder-lock assertions pass; all 14 inherited test scripts pass.
- JDK21 `javac --release 11`: 1,277 Java sources → 1,388 classes. Independent fresh extraction rebuilt JAR SHA-256 `ed092c2e56967cee501c6e120f915ac10810cc9adb375cd9efba4e86d2dbebf3`.
- Local public verifier: 39 synthetic tests pass; generic scratch-only JDK probe tested separately. Hosted CI is **synthetic-only**, not proof of private client runtime behavior.

## Explicit limitations

No original v309 binary parity, game launch/login/reconnect, Windows private-runtime test, v312 compatibility, actual user-cache migration, authenticated writer identity, power-loss fsync durability, multi-file transaction or safe stage cleanup has been demonstrated. The original v309 binary, production v312 client, updater, caches and game server remain untouched.

**Public PR content:** only verifier, SHA witness, synthetic tests, generic Java probe, CI workflow and this report. No private Java sources, executable JAR or binary dependencies.

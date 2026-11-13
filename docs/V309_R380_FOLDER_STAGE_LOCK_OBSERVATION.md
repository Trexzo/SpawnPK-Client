# R380 — cooperative folder-stage lock observation (private v309 candidate)

**Repository:** `Trexzo/SpawnPK-Client`, stacked on draft R379 PR #1174. **Keep draft and unmerged. Private source release gate CLOSED.**

## Why this pass exists

R379 can perform a momentary cooperative lock probe for `order.settings` staging, but older `.loadout-stage-<random>.pending` folder-data staging names do not encode which per-folder lock corresponds to them. Looking at the lock file's existence does not prove a lock is held, while an unlocked lock **does not prove a stage is stale or safe to delete**.

## Private implementation scope

One recovered source file changes: `rs/gui/loadouts/io/LoadoutStore.java`, among 1,277 pinned Java files. R380 changes newly-created folder-data staging filenames to:

` .loadout-stage-<32 lowercase hex characters>-<random JDK temp suffix>.pending `

The 32 hexadecimal characters are derived from the pre-existing SHA-256-based folder lock naming function. They correlate a newly staged payload with the matching `.loadout_lock-<digest>.lck` cooperative lock. **They are not a cryptographic privacy guarantee for easily guessed folder names.** Older, uncorrelated stages remain **unknown**.

The diagnostic checks the stage and lock metadata without following symbolic links, opens an **already existing** lock only (never creates it), obtains an optional nonblocking `FileLock.tryLock()` observation, and releases any acquired probe lock immediately. Busy/free/unavailable/unsafe/absent statuses explicitly state `OWNER_UNKNOWN`. It does **not** identify a writer, read staging contents, quarantine or delete data, or authorize automated cleanup. An outside writer can ignore the cooperative lock entirely. Observations may become stale immediately.

## Local verification using the actual private recovered source

- SHA-256 pinned R379 private ZIP `e23d2483b0acd27939e6b467ae6bf4e8b9f25652f57d3523fe93c32f8bb523ca` → R380 SHA pinned source ZIP **`2ff9eb506ac001cb0c63f0dc1cbaf45fd322af33bb4191146afcdc88c1b8b3a6`**. Exactly `LoadoutStore.java` changed.
- New source-backed scratch Java suite: **24/24 assertions PASS**, including real second-JVM lock contention, legacy stage handling, bad suffix, missing/unsafe/symlink lock, unsafe staged symlink, immutable sorted observations, and preservation of stage and lock bytes.
- All inherited source-backed scripts pass (442 previously documented assertions including R379); notably R379's 32 order-lock assertions remain green.
- Full OpenJDK21 `javac --release 11`: **1,277 sources -> 1,388 classes**, no compile error. Full independent extraction of private build kit reproduced JAR SHA-256 **`48539b2291994584bd7c589588487b35371f9f6ece21b43763c126d73d6fec0f`**.
- Public SHA archive verifier: **31 synthetic tests PASS locally**, plus **16 assertions** of the generic scratch-only JDK probe on Linux. Hosted Windows/Ubuntu results must be independently checked and do not execute private game code.

## Limitations

No power-loss/fsync durability proof, full multi-file transaction, stage/process ownership certificate, safe cleanup, original v309 binary parity, genuine Windows private-runtime acceptance, original game GUI/login/reconnect, v312 compatibility, or uncooperative-writer protection. No production runtime, owner cache, original JAR, updater or live server changed. **Keep PRIVATE SOURCE / DRAFT / UNMERGED.**

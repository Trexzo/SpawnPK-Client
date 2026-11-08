# R367 — loadout-file concurrent modification protection (private candidate)

**Repository:** `Trexzo/SpawnPK-Client`. Stacked on R366 PR #1159. This is a **source-backed candidate**, not a release. The private source and dependencies are intentionally **not committed** to this public repository.

## Reproduced failure in R366

R366 validated an existing folder, staged new bytes and used `ATOMIC_MOVE`/`REPLACE_EXISTING`. An external process can replace the existing, fully valid folder **after validation but before the atomic move**; R366 overwrote those external changes without detecting the conflict. The test injects a deterministic write through a Java List's iterator during stage serialization. The modified file has the **same length**, avoiding accidental success from length comparisons. The R366 source-backed fixture fails `EXTERNAL_VALID_SAME_LENGTH_WRITE_LOST`; the R367 candidate passes.

## Private R367 change

Exactly **one owner-private recovered Java source** differs: `rs/gui/loadouts/io/LoadoutStore.java` among 1,277 verified files.

- A raw byte SHA-256 fingerprint is calculated before the existing version-aware readability check.
- A second fingerprint is calculated **after staging** and immediately before atomic rename. An altered, deleted, or newly created destination refuses replacement and cleans up staging.
- Nonregular targets (e.g., symlinks) are refused rather than followed by the fingerprint step.
- `saveFolder` is synchronized per store instance. There is **no system-wide lock**, cross-process compare-and-swap, durable transactional version-marker update or guarantees against a change occurring **between the final check and rename**.
- The existing v5 on-disk format and existing UI callers are unchanged. Refusals currently log to `System.err` and **are not shown in the GUI**. GUI conflict reporting requires a separately tested UI change.

## Owner-private verification

The private R366 baseline ZIP is pinned by SHA-256 `107110c74a57e6feaa5d7fd72a13e386c36c13bd354191fbe305704fd59cc1b3`. The R367 source ZIP and owner hashes are pinned in the public witness JSON. An independent full archive comparison verified **1/1,277 changed**. All other 1,276 Java sources are byte-identical to R366.

**R366 reproduction:** isolated source-backed test fails the same-length external-mutation assertion. **R367 regression:** 30 Java assertions pass including healthy read/write, damaged original preservation, versions 1–4, same-length conflict, creation/removal during stage and cleanup. The inherited R365 serializer tests also passed 60 assertions across UTF-8 and ISO-8859-1.

OpenJDK21 `javac --release 11 -proc:none -g:none` compiled all **1,277** sources to **1,386** `.class` files. Fresh extraction of the complete private build kit rebuilt an **identical** JAR SHA-256 `3fd721e254279cca0bc66c97cdfbde6b2436c83b2fb72bc02e9a6cdbcb8ed872`.

Public CI is restricted to synthetic ZIP/source-manifest tests, not the 1,277 private Java files. No game login, original-v309 binary parity, GUI runtime or real user cache was tested. Power-loss durability and simultaneous external writer at final rename remain **unproven**. The source milestone publication gate remains **CLOSED**, draft PR stays **UNMERGED**, production v312, updater, original JAR/cache and server untouched.

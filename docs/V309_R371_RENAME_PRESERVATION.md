# R371 — preserve loadout folder on failed rename

**Correct repository:** Trexzo/SpawnPK-Client. Stacked on R370 PR #1163. Reconstructed private v309 Java sources remain owner-private.

## Reproduced failure in unmodified R370
The original recovered LoadoutFolders.renameFolder method deleted the old on-disk folder before writing the renamed destination. A source-backed test placed an unrelated directory at the destination name: the new save failed, but the original folder bytes had already been removed. Baseline test result: R370_BASELINE_RENAME_DATA_LOSS_REPRODUCED. This is an offline fixture, not a live-cache incident.

## R371 candidate
Exactly two reconstructed Java source files changed out of 1,277: LoadoutFolders.java and LoadoutStore.java. The public repo contains no private Java files or dependency JARs.

- Existing void saveFolder and void writeFolderOrderSettings methods remain available; additional checked variants return true only after their corresponding data/metadata operations complete.
- Refuse rename when the source is missing, symlinked, or unreadable. Do not silently discard a corrupted trailing record.
- Refuse hidden preexisting rename destinations and stale version/temp metadata rather than overwriting someone else's disk data.
- Save new folder data before changing the in-memory GUI map; write the new order.settings before deleting old data.
- On a failed destination save, retain old bytes and GUI state. If ordering fails, restore the old in-memory GUI map and retain both old and newly written copies as recovery evidence.
- Reuse non-modal GUI failure feedback. Successful rename writes v5 data and marker.

## Owner-private verification, not hosted CI
- Unmodified R370 bug reproduced using actual recovered Java source compiled with temporary GUI stubs.
- R371 new source-backed rename assertions: **23 PASS**.
- Inherited source-backed tests: 44 store + 28 order.settings + 29 version-marker + 60 serializer (UTF-8/ISO-8859-1), **161 PASS**.
- JDK21 javac --release 11: **1,277 Java source files -> 1,386 class files**, full compilation PASS.
- Independent fresh extraction and private build kit replay reproduced rebuilt candidate JAR SHA-256 `0c3f51374aea0d938325856ebbc6d088260e0304d795f502ed9a2a1818e3e170`.
- Prior R370 private source ZIP SHA-256 `df72e08423b4eb4ac030e92e3cad4743c9c98465131220624ffda4553ab05eb0`.
- Candidate R371 private source ZIP SHA-256 `8b5e5c14b088ead3e92546148c4550ad2db51f5fb8cb81dac498076d561766d2`.
- Private reproducible build kit SHA-256 `5469dde77ee17db665a14293461a8848b2dbf2cb4f464fbdd9bc45f145c5e709`.
- Private delivery package SHA-256 `06bfe4bafee02592d04a52f13ea8e83f537623dbfc5cd7480931336f4016aa4d`.

## Limits and release gates
**This is not a multi-file transaction.** A crash between saving new data and old-file retirement can leave both copies; the subsequent folder scan can display both. Old-folder deletion is still best effort, and uncooperative writers can race source validation/retirement. No fsync/power-loss durability, real GUI, original-v309 ABI or runtime equivalence, login, reconnect or v312 compatibility is established. The hosted 4-way Python CI verifies *only synthetic witnesses*; the private Java-source checks are separately executed evidence.

**PRIVATE SOURCE RELEASE GATE CLOSED. DRAFT/UNMERGED.** No production v312, signed updater, original v309 JAR, owner cache, credentials or game server modified.

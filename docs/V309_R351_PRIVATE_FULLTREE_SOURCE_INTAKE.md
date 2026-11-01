# R351 — private full-tree v309 Java candidate intake

**Destination:** `Trexzo/SpawnPK-Client`. This source-reconstruction milestone does **not** belong to `fullspkclient-private`, SpawnPK-RE, or the production v312 client.

## Real owner-library source recovered

The owner Library contains `SpawnPK_v309_R211_COMPLETE_SOURCE_PRIVATE.zip`, which was opened and inspected in this work. Exact archive SHA-256:

`3f8ade7a37a1c8fe21dea367cf48660418c25a4905d943fe9358aa8846c275f0`

The ZIP has **1,275 Java files** at `src/**/*.java` and one `PRIVATE_SOURCE_SHA256_MANIFEST.json`. It includes Java sources for `rs/Client.java`, `rs/Configuration.java` and `rs/gui/Launcher.java`. Those three paths are *not* just source-file placeholders. Observed approximate readability coverage:

- **307** files named `Class<number>.java`.
- **894** files containing `field<number>` identifiers.
- **809** files containing `method<number>` identifiers.
- The source tree is approximately **8.0 MB** of Java text, not an empty stub.

The R315 indexed source manifest describes **1,277** Java files. **Do not** claim this R211 1,275-file tree is byte-identical to R315 or infer which two files are absent solely from the count.

Two independently known R315 file SHA-256 values do match this R211 archive byte-for-byte:

- `rs/Configuration.java`: `71144e19558144be9a330d87a968e1eeb8d1818d1e56ec31b3ab6d4a72de084b`
- `rs/gui/Launcher.java`: `b6ca18660de26eb49dfd618249ba2b6b31d4be78a4af35a88eb018baf314689f`

R211 `rs/Client.java` is **897,987 bytes** / SHA-256 `cba90830e8212ffdf59baaefe9ff16ebab6c314509de93624ea9dc3348f9aed7`; the later R315 manifest lists **898,413 bytes** / SHA-256 `f7d8e18a5e5d0b43e25b579388d06f035e0890dc8d595c41aac56bb316fc9dcf`. They are different candidate revisions, so no arbitrary replacement or silent source-tree mixing is accepted.

The R211 `rs/Configuration.java` explicitly includes added `spk.serverHost` and `spk.serverPort` properties and explanatory developer comments; this is **edited reconstructed source** and **not original-author source text or verified original-JAR endpoint behavior**.

## Concrete deliverable

`scripts/prepare_v309_r211_source_candidate.py` makes this full candidate tree repeatable:

1. Requires the **exact R211 archive SHA-256** and all 1,275 Java members.
2. Verifies each file against the archive's original SHA-256 manifest.
3. Refuses ZIP traversal, symlink entries, non-source members, case-insensitive path collisions, unexpected sizes, and reused output directories.
4. Writes every unchanged candidate Java file into a **new private directory**, plus `PRIVATE_CANDIDATE_MANIFEST.json` with source-tree SHA-256 and per-file readability flags.
5. **Does not claim semantic names, clean compilation, original-JAR parity, a full certified v309 release or authenticated game runtime.**

Command, when the archive is available on a machine with Python 3.11+:

```powershell
py -3 scripts/prepare_v309_r211_source_candidate.py `
  --archive "C:\private\SpawnPK_v309_R211_COMPLETE_SOURCE_PRIVATE.zip" `
  --new-private-output "C:\private\v309-r351-source-candidate"
```

Only use a fresh, private destination: never `recovered-source/v309/src` until it meets the existing [Source-M1 publication gate](SOURCE_MILESTONE.md) with complete source identities, Windows-legal filenames, zero project-binary fallback, clean build, and independent provenance checks.

## Next work toward **readable deobfuscated code**

Use the staged tree as the full **candidate** baseline; then prioritize verified original-v309 mapping of `Class<number>`, `field<number>`, `method<number>`, source/JVM type-owner references, and private compiler diagnostics. Existing R124–R130, R181–R192, and Source-M1 research in this **correct** repository is authoritative starting work and must not be duplicated in an unrelated project.

No original client JARs, runtime caches, credentials, or raw decompiled Java are committed to this public repository. CI uses only synthetic miniature ZIPs. Actual private R211 source and any future build outputs remain outside Git. The connected owner desktop was offline at this milestone; no new original v309 Java runtime/build acceptance is claimed.

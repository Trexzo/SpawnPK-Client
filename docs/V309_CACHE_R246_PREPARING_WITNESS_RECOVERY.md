# Cache R246 — persisted install witness during PREPARING

**Lane B ownership:** Only the private v309 Java cache transaction helper. Shared coordination is issue #1117; Chat A owns the canonical GUI, networking, asset recovery and world-rendering client.

## Reproduced failure

Between `writeInstallWitness(work,...)` and `writeState(work, root, "STAGED")`, a crash leaves a V2/V3 **PREPARING** journal with a valid on-disk `.install-witness`. R245 treated PREPARING as always witnessless. An actual R245 Java regression reproduced silent cleanup of an empty staged tree and journal when the witness recorded HAD_ORIGINAL but the live original had disappeared.

R246 reads an existing PREPARING installation witness and refuses restart recovery if the witnessed original's presence contradicts the live root, if the staged directory is missing, if unexpected `previous/` exists, or if staged bytes differ from its persisted SHA256 fingerprint. On contradiction it preserves stage and journal for inspection. Truly witnessless PREPARING and consistent first-install/old-cache recovery remain compatible. This is applied on restarted V2/V3 transactions; in-process failed downloads retain the separate safe cleanup path.

## Actual private validation

- **Exactly one changed production source:** `src/rs/cache/updater/assets/CacheUpdateTransaction.java`.
- Required R245 source preimage SHA256: `d32012d42342b5888ff35b9025bb66270d9b95c3538275ec4843c79ae97cf1fa`.
- R246 postimage SHA256: `030284641b3ce50a6e9324bb2bc96c83b8a2982db0ffd8fa41330b4139615ed2`.
- Exact review diff `tools/java/r246/R246_EXACT_SOURCE_REVIEW.diff`: **1,527 bytes**, Git blob SHA1 `8fd001fa95b154fe8eec100e3080d46991ea19dc`; byte-identical to private source comparison.
- Complete actual private `javac --release 11 -proc:none -g:none`: **1,277 Java sources → 1,388 classfiles, zero errors**. Precisely one production source and one compiled classfile differ from R245.
- **33/33 offline regression Java programs PASS**, including new R246 PREPARING persisted-witness regression **65 checks**. It tests V2/V3 HAD_ORIGINAL with missing live root, NO_ORIGINAL with foreign live root, corrupted stage fingerprints, consistent original, genuine first install, and witnessless/V1 legacy compatibility.
- One inherited R238 regression was adapted **test-only** to preserve a mismatch with an existing PREPARING witness until deliberate operator-equivalent reconciliation. The original fixture remains in the package.
- A first full regression run had **32/33**, exposing that obsolete inherited fixture assumption; the clean adapted full rerun passed all **33/33**. Windows-only alias branch compiled but did not execute on Linux.

## Verified deterministic private package

- Complete ZIP: `SpawnPK_v309_R246_PREPARING_WITNESS_GUARD_PRIVATE.zip`, **SHA256 `386159028dd9fb29f37432bca3c2c3588e43d07a6d874e5a0e6ddfa95d35d830`**, 22,564,381 bytes, 70 entries.
- Inner incremental R245→R246 ZIP SHA256 `64d5e3939fe46cb02c4e4d8d18332efde966ac5582fc0e7c498446fc5b17a604`.
- Inner cumulative R234→R246 ZIP SHA256 `2a498a2208286da2af77830de015a56ddbcbcd50698106ae514fd14c1df93dea`.
- Complete private source ZIP SHA256 `4ae25465bdc3539f0b89fff28d82e3390214c198fd34183d1cd45025ed0a67ce`.
- Source-built Java11-target class JAR SHA256 `7906450e8ac5310620bf6ee0b6472be665ccd4a31fe62421feecfec08558261a`.
- Constructed ZIP twice with identical bytes and SHA256; outer/inner ZIP CRC and hashes verified. Includes 33 regression sources, original and test-only adjusted fixture, build logs, exact compile dependencies, full source, compiled JAR, SHA-pinned PowerShell one-file overlays with preimage backup and rollback and Windows rebuild/test runners.
- **Packaging repair:** prior R245 Windows rebuild script referenced `$Manifest.inputs_sha256` even though that map did not exist. R246 manifest includes complete actual source/dependency SHA256 values; all 33 tests referenced in its Windows runner are present in the archive. This does **not** amount to execution on native Windows.

## Direct one-file integration for Chat A

Across **13 actual complete R234–R246 private donor snapshots**, the **other 1,276 production Java files are byte-for-byte identical**. Therefore a currently R234 canonical helper may use `R246_Apply_R234_CumulativeOverlay.ps1` to replace **only** `CacheUpdateTransaction.java`, if and only if the actual preimage SHA256 is `bc08aff2ddd3948f5ea8c248100234a39ee03cafd66b24e27b48c85e91aa2cad`. The supplied incremental R245→R246 overlay requires the exact R245 preimage above. An unknown hash must **STOP**; never overwrite Chat A's complete source tree.

After application, Chat A needs to rebuild/test its **actual current canonical** Java source and recheck cache, GUI, localhost world/network and shader/asset integrations. Private donor verification alone does not prove integrated GUI/gameplay acceptance. The public PR contains source review and documentation, **not** the proprietary source-built client or hosted R246 Java CI. Native Windows gameplay, physical power-loss, malicious metadata edits and post-check external writer races remain unverified. Keep draft, no main merge.

# R447 — Original v309 client class and asset coverage mapping

**Repository:** Trexzo/SpawnPK-Client  
**Parent:** R446 draft PR #1242  
**Status:** DRAFT / UNMERGED / NOT DEPLOYED.

## Why this advances the complete client reconstruction goal

The existing Loot Tracker work R415–R446 established careful persistence and private Store source/class gates but did not map **all original client functions and resources** or prove that a full runnable client can be assembled. R388 previously inspected the SHA-pinned original v309 client JAR and found **10,502 class files and 419 non-class resources**; the recovered class-only source build at that stage emitted **1,388 compiled class files**, and a preferred filtered dependency JAR supplied most third-party/legacy classes. The later R421 private Store/plugin changes compile **1,277 Java sources to 1,394 classes**. Original class names are not necessarily equivalent to deobfuscated or reconstructed names; mere path coverage must not be confused with bytecode parity or successful launch.

R447 adds a **read-only, original-vs-rebuilt namespace and resource coverage map** distinct from the missing historically approved R421 manifest blocker. It helps identify where original Java classes appear to be missing, where the reconstructed classes fall outside the original namespace, what classes exist only in dependencies, and how many original resources are present and byte-identical in an already-preserved *private* resource companion.

## Original source JAR pin and exact input scope

The original v309 `client.jar` is required and pinned to SHA256:

```
ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38
```

The script refuses a different JAR or any original count other than exactly 10,502 class paths and 419 non-class file paths (ZIP directory entries excluded). The original ZIP is read with a bounded stable nofollow file reader (256 MiB maximum) and inspected using Python's ZIP central directory. No extracted files or Java execution are needed. Duplicated ZIP entries, relative-path traversal, link/special members, encrypted entries and excessive entry counts or claimed uncompressed sizes are rejected.

The reconstructed input remains **only** the exact isolated owner-TEMP R421 source/class and dependency roots enforced by R440/R446, including original pinned Store Java and class SHA, exactly 1,277 Java sources / 1,394 compiled classes, and the two legacy filtered JARs R239_filtered.jar/R218.jar. Each dependency JAR is independently parsed as a ZIP; the preferred runtime set is the **union of the compiled R421 classes and R239_filtered.jar classes**. The R218 alternate is counted separately for overlap. This does not install a JAR, merge a classpath, or invoke a loader.

The script reports *aggregate counts only* by default:
- original classes / original non-class resources;
- 1,277-source/1,394-class observed R421 inputs;
- unique class names on reconstructed + preferred dependency classpath;
- original class names present and absent from that classpath;
- reconstructed classes with names absent from the original client;
- overlap among reconstructed and preferred/alternate dependencies;
- source/class filename association **heuristics** (not proof of Java ownership);
- optional original resource companion count: matching, mismatched, missing, extra.

### Resource companion byte comparison

Pass `--resource-companion-root` only for an **already existing isolated, privately preserved** copy of the 419 original non-class resource entries. R447 verifies the selected tree has no links/special files, enforces directory depth/member caps, and compares actual content SHA256 **against each original pinned JAR resource entry** without extracting or rewriting any resource. It reads bounded resource bytes, and never sends file contents to GitHub or the game server. This confirms only whether resource *input* parity is present, **not** that a reconstructed runnable JAR packages or loads those files.

## Owner execution — no installed client access

On the authorized owner PC, once the historical R421 isolated TEMP tree is present and the original SHA-pinned v309 JAR is accessible, run from the GitHub checkout:

```powershell
python -B tools\r447\audit_original_class_asset_coverage.py --original-v309-jar '<owner-local exact original v309 client.jar>'
```

With an existing isolated resource companion:

```powershell
python -B tools\r447\audit_original_class_asset_coverage.py --original-v309-jar '<owner-local original v309 client.jar>' --resource-companion-root '<owner-local resource companion>'
```

An **optional explicit** `--save-private-unapproved-name-map` flag reruns the full audit to confirm stable inputs before creating a **new** private OS TEMP quarantine file `R447-UNAPPROVED-ORIGINAL-COVERAGE.json`. This file includes original class **names** absent from the reconstructed classpath, compiled class names not seen in the original, source-file-name heuristics, and resource paths that need investigation. It contains **no Java code, game binaries, player history, credentials, journal records or raw original JAR resource contents**. The output is intentionally marked **UNAPPROVED**, with `compilation_authorized:false` and `release_authorized:false`; do not upload or paste the private name map into a public repository.

No output file or client change occurs without the explicit save flag. This tool does not compute or self-approve R442's historical baseline digest.

## Verification and limitations

Twenty-four synthetic tests use invented Java/class names, dummy ZIP bytes, fake dependencies, and temporary resource companions to check coverage arithmetic, exact original SHA refusal, safe ZIP entry rules, duplicate/oversized paths, missing and mismatched companion assets, symlink refusal, no-write default, explicit private quarantine, tamper between audits, and nondeployment flags. Windows/Ubuntu × Python 3.11/3.13 CI also runs inherited R446/R445/R444/R442/R441/R426 suites. **No actual owner-private JAR, resources or 1,394 compiled classes are present in GitHub CI.**

A static class-name census is not bytecode parity: renaming and obfuscation, reflection, JNI, plugin loading, optional dependencies, resource lookups and original server protocol can differ even when every class name overlaps. R388's constant-pool closure audit remains separate. R387/R388's original resource companion evidence is not a packaged complete client. R440/R425/R432 acceptance and R427–R431 actual `LootHistoryStore`/`LootTrackerPlugin` integration are also separately pending. The **full readable, deobfuscated, runnable and asset-complete SpawnPK client is NOT yet established**.

**Release and merge stay closed.** No client startup, real player history access, production persistence modification, R415/R417 deletion-journal cleanup or installation occurred.

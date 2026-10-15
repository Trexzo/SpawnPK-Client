# R182 — read-only javac transcript frontier (initial slice)

Parent: [#1073](https://github.com/Trexzo/SpawnPK-Client/issues/1073), source milestone [#1004](https://github.com/Trexzo/SpawnPK-Client/issues/1004).

This branch deliberately implements a **small, honest first step**: ingest an existing private `javac -XDrawDiagnostics` UTF-8 transcript and produce a SHA-pinned, deterministically sorted JSON report. It does **not** invoke javac, load original binaries, classify unseen dependency causes, or claim a client build.

Example (private workstation, replacing paths/digest):

```powershell
$Transcript = 'C:\private\v309\javac-xdrawdiagnostics.txt'
$Expected = (Get-FileHash -LiteralPath $Transcript -Algorithm SHA256).Hash.ToLowerInvariant()
python tools/javac_frontier_r182.py $Transcript --sha256 $Expected --profile jdk9-only-r179 --output 'C:\private\v309\frontier-r182.json'
python -m unittest discover -s tests -p 'test_javac_frontier_r182.py'
```

**Warning:** calculating the digest from the same file is only a local consistency check; a separately pinned expected digest is required for independent authority. The output contains source paths and error messages; keep it private unless explicitly reviewed for disclosure.

## Implemented scope
- Requires SHA-256 and a bounded explicit build profile.
- Parses standard one-line `-XDrawDiagnostics` source-position records.
- Stable sorted output, retains every nonempty non-summary unparsed line.
- Reports a separate parsed/unparsed count.
- Labels every root cause `unknown`, not a speculative external library/class/alias classification.
- Exclusive-create output; won't overwrite previous reports.
- Synthetic regression tests only.

## Still outstanding under #1073
- Full command/toolchain and dependency provenance, transitive binary screening, source inventory.
- Multiline and other platform-specific diagnostic structures (currently preserved under unparsed).
- Total raw javac errors independently attested.
- Evidence-backed root-cause classification and per-owner graph.
- Ubuntu/Windows CI, private 1,279-file exact replay, and full-source build.
- Comparing identical-profile before/after outputs (not yet supported).

**No decrease from the last reported 2,343 JDK-only compiler errors is claimed.** The older 516-result used a different dependency profile and must not be compared directly.

## Same-profile comparison extension

`tools/javac_frontier_compare_r182.py` now accepts two SHA-pinned JSON reports and their independently pinned profile-lock files. Required lock fields: `toolchain_sha256`, `javac_command_sha256`, `dependency_manifest_sha256`, `source_scope_sha256`, and `dependency_policy` (`no-original-client-binary`). It rejects differing locks, incomplete diagnostic inventories, transcript count mismatch, and conflicting build labels. Its output contains aggregate counts only, not private source paths or diagnostic messages.

Example:

```text
python tools/javac_frontier_compare_r182.py --before BEFORE.json --before-sha256 PIN --after AFTER.json --after-sha256 PIN --before-lock LOCK1.json --before-lock-sha256 PIN --after-lock LOCK2.json --after-lock-sha256 PIN --output DELTA.json
```

**Strict limit:** A matching lock claims comparison eligibility; this tooling does not itself verify that the lock truthfully describes the compiler, input set, or transitive dependency closure. The lock fields are a future integration contract, not authoritative provenance. No cause classification or private v309 compilation has been performed by this branch.

## Source and dependency manifest stage

`tools/source_manifest_r182.py` inventories each Java file in a private source directory with its relative POSIX path and SHA-256, recording a deterministic source-scope digest. Case-insensitive source-path collisions reject the inventory to avoid silently losing files on Windows.

A separately reviewed JSON object maps explicitly approved dependency basenames to expected SHA-256 values. The tool rejects unapproved, malformed, duplicate-member or case-colliding JAR/ZIPs and known client-code namespace class entries (`rs/`, `com/jagex/`, including versioned `rs/` class paths). The output contains the source paths/hashes and must remain private.

Example:

```powershell
python tools/source_manifest_r182.py --source-root 'C:\private\v309\recovered-source\v309\src' --approved-deps-json 'C:\private\approved-dependencies.json' --deps 'C:\private\dependencies\library.jar' --output 'C:\private\v309\source-manifest-r182.json'
```

This stage is an **inventory and fail-closed heuristic guard**, not an independently authenticated source provenance statement. A JAR lacking the known forbidden namespaces is not thereby proven legitimate. Transitive/Maven resolution, shaded or relocated original classes, zip bombs, nested archives, packaged dependency trees, source code authentication, license review, toolchain command fingerprints and compiler execution are outside this stage. The prior R182 profile-lock comparator still relies on caller-supplied source/dependency digests; automatic authoritative lock generation is not implemented.

Synthetic test command:

```powershell
python -m unittest discover -s tests -p 'test_*r182.py' -v
```

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

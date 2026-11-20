# R445 — Bound all owner-TEMP evidence discovery and stable original Store reads

**Parent:** R444 draft PR #1240. **DRAFT / UNMERGED / NOT DEPLOYED.**

## Verified public facts

- Exact R444 head passed the 4-job Windows/Ubuntu CI. The last separate Recovery CI was running.
- Authorized owner device `DESKTOP-LTXXO4K` was checked for R445 and remains **offline**. No user-PC R421 scan occurred.
- The reachable connected private repository `Trexzo/fullspkclient-private` currently has 71 main-branch commits ending August 26, 2026. `Trexzo/fullspkclient-current` has only its November 17 bootstrap commit. These checked trees do not contain the required R421 reference; there may be other unexamined local archives.
- The archived owner-private R315 source manifest has 1,277 source entries and dependency hashes but **lacks** a complete 1,394-class R421 inventory. It cannot authenticate R421 source/class custody.

## Concrete R444 shortcomings fixed

1. `evidence_dirs()` used `sorted(temp.iterdir())` before checking the 24-candidate cap, so listing very large TEMP directories could consume unbounded memory and time even when no historical owner candidates matched. R445 independently caps the top-level and isolated-parent listings at 6,000 entries *before sorting*, and refuses oversized roots without claiming nothing was found.
2. `source_class_count()` used `os.walk()` without bounding the number of *directories* or depth, and without limiting the initial size of each directory's member list. R445 uses an explicit non-following iterative walk limited to 1,800 directories, 7,500 total entries, and depth 36. It preserves the existing exact R444 symlink and special-file rejection contracts; over-budget is an explicit refusal, not a verified absence.
3. `exact_store_pin_matches()` called an unbounded file-hashing helper against the observed Store Java/class files. R445 allows at most 2 MiB per exact Store file and uses a checked fd to reject changed inode, size or modification time **before and after reading**. `O_NOFOLLOW` and `O_NONBLOCK` are used where offered by the OS. No file path, hash or bytes are printed. An oversized original Store is refused rather than hashed or silently counted as a match.
4. Candidate manifest shape reads now share this bounded file reader, retaining the existing 4 MiB maximum, duplicate-key refusal, and exact R442 candidate-source/class SHA checks. A shape match remains diagnostic only—never verified historical approval, a class compile receipt or release authorization.

All scans remain restricted to the previously known owner-TEMP R421/R425 evidence paths. The scanner does not read arbitrary `fullspkclient` directories or live player history, launch games, run Java, create files, touch deletion-intent/ack/lock evidence, or auto-approve the original source/class manifest.

## Public test evidence

16 new synthetic Python regression tests exercise oversized TEMP roots, isolated-parent enumeration, source/class tree total-entry and directory limits, depth, oversized pinned Store files, fd-open/read mutation races, symlinks, oversized and valid candidate manifests, no private path/digest output, no writes, and explicit read-only CLI. Cross-platform Windows/Ubuntu × Python 3.11/3.13 CI runs inherited R444→R440 and R426 synthetic acceptance tests.

**R445 is useful scanner hardening, not completion of the original goal.** No R421 owner-private reference was recovered and there was no real R442, R440, R425 or R432 acceptance. The real client-source reconstruction, executable JAR/resources parity, R427–R431 asynchronous `LootHistoryStore`/`LootTrackerPlugin` adapter, Swing EDT responsiveness, v312 restart and actual user-facing runtime remain unverified.

## Real next gate

When the owner PC becomes reachable, execute `python -B tools/r444/scan_owner_r421_artifacts.py --owner-read-only-evidence-audit` on the explicit isolated owner TEMP workspace. Interpret aggregate results without assuming provenance. If a previously approved 1,277-source/1,394-class R421 manifest exists, validate its independent reference SHA and full entries with R442 first. Only then R440 read-only and separately opted-in R425/R432 acceptance. Do **not** manufacture an expected SHA from current files to make those checks pass.

Keep every staged PR draft/unmerged. No merge, JAR install, source upload, history deletion, persistent intent/ack removal, write unlocking, or deployment is authorized.

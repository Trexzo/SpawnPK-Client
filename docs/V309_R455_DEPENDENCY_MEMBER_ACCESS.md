# R455 — Inspect selected dependency JAR members and flag JVM access uncertainties

**Repository:** `Trexzo/SpawnPK-Client`  
**Parent:** R454 draft PR #1251; inherited R454 four-job matrix verified.  
**Status:** DRAFT / UNMERGED / NOT DEPLOYED.

## Why

R453 inventoried rebuilt `CONSTANT_Fieldref`, `CONSTANT_Methodref`, and `CONSTANT_InterfaceMethodref` JVM member triples. R454 found direct and possible inherited declarations inside recovered R421 classfiles. But both previously treated preferred dependency `R239_filtered.jar` only as a **set of filenames**, not as a source of member declarations. A known class name is not evidence that a dependency provides the requested method or field.

R455 adds a read-only, bounded parser for **selected needed dependency classfiles**. It can identify exact `owner:name:descriptor` declarations in the preferred JAR and record access-control risks without pretending to execute a JVM or implement the JVM verifier/linker.

## Scope and limits

`tools/r455/dependency_member_access.py` first validates the SHA and entire preferred JAR central directory through R447. It selects only dependency classes directly named by rebuilt member references or appearing as superclass/interface edges in the rebuilt tree, then follows additional needed preferred-dependency superclass/interface edges. It limits selected members to 2,048 classes, 8 MiB uncompressed per class, 64 MiB total selected bytes and 8,192 queue steps; class content is read via ZIP APIs with CRC checks and internal class-path agreement.

The underlying R453 class parser now has **an explicit optional major-version allowlist (45–55)** for selected historical dependency classfiles. Default R453/R454 reconstructed classfile analysis still requires exact Java 11 major 55. Dependency classfiles newer than Java 11 fail closed as unsupported rather than being treated as working.

R455 merges selected preferred dependency class metadata with rebuilt R421 class metadata, preserving reconstructed-class precedence, and inspects only references originating in rebuilt classes. It reports exact direct declarations, possible superclass/interface inherited declarations, and uninspected/missing owners. For declarations observed in selected dependency classes it compares access flags and marks:
- Public member with classloader/module accessibility **unverified**.
- Private member with **same-class or nestmate access unverified**.
- Protected member with package/subclass/receiver constraints **unverified**.
- Package-private member in same package as an advisory candidate, or cross-package as a **possible access risk**.
- Nonpublic declaring class as a separate **visibility uncertainty**.

These are conservative signals, **not JVMS linkage decisions**. The analysis does not track `invokevirtual` vs `invokestatic` callsites, field static/instance access, real classloader package equivalence, nest host membership, modules, protected receiver classes, default-method conflicts, runtime dispatch or JNI. Classes absent from the selected archive or with unknown external ancestry remain unresolved; `R218.jar` is inventoried as an alternate source of names only.

## Owner safety gates

`tools/r455/audit_dependency_member_access.py` runs R454→R453→R452→R451→R450→R449→R448→R447→R446 validation first. It requires:

- Exact pinned original v309 `client.jar` SHA256 `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38` and exactly **10,502 original classfiles and 419 original resources**.
- Owner-isolated current R421 tree of **1,277 Java source files and 1,394 compiled Java 11 classfiles**, with existing fixed `LootHistoryStore.java` and `LootHistoryStore.class` hashes.
- The exact preferred `R239_filtered.jar` and alternate `R218.jar` SHA values recorded in R446, per-file reconstructed class SHA rechecks, exact original SHA and entire current inventory rechecks afterward.
- An independently approved **historical** R421 source/class manifest is **still missing**. These current-file SHA comparisons do not create or approve one.

No Java class is executed, no client is started, no private source is uploaded, no assets are built/installed, no game player-history data or credentials are inspected, and no R415/R417 deletion marker/write-fence is changed.

## Owner-only invocation

Read-only aggregate-only stdout when the authorized owner machine is available:

```powershell
python -B tools\r455\audit_dependency_member_access.py --original-v309-jar '<owner-local pinned v309 client.jar>'
```

To explicitly save a private worklist of class/member names, access flags and possible referencers:

```powershell
python -B tools\r455\audit_dependency_member_access.py --original-v309-jar '<owner-local pinned v309 client.jar>' --save-private-unapproved-worklist
```

Private saving independently runs the entire audit twice, compares results and exact full owner source/class/dependency SHA inventories, then creates a **new exclusive owner OS TEMP** folder with `R455-UNAPPROVED-DEPENDENCY-ACCESS.json`. No earlier worklist is overwritten; no reconstructed source or class bytes are copied. Never upload private reports to GitHub.

Optional `--resource-companion-root` preserves the inherited read-only original-resource byte comparison, not a resource packaging claim.

## Public CI and next gaps

Public synthetic Windows/Ubuntu × Python 3.11/3.13 tests cover selective ZIP extraction, class name/CRC/budget/major checks, direct and inherited dependency method declarations, exact signature mismatches, public/private/protected/package access risk classification, unstable inventories, no-write defaults, missing original, and opt-in private quarantine. **34 new tests**, plus R454→R445, R442, and R426 inherited regression suites. No real owner JAR, recovered source or game history enters hosted CI.

The authorized owner PC `DESKTOP-LTXXO4K` was offline at R455 intake. The full readable source/client recompile+link, asset-complete client.jar assembly, visual GUI startup, real login/gameplay/FPS and v312 runtime compatibility remain unverified. The next important technical step is verifying selected invocation opcode/staticness and actual class/method access constraints before claiming compatibility, followed by independently approved R421 provenance and real owner-side compilation/runtime acceptance.

**Keep R455 draft/unmerged. No production JAR replacement, private source export, history modification, write-fence unlock, journal cleanup or release authorized.**

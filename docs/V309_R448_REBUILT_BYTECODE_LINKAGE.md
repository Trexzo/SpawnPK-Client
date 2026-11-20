# R448 — Prioritize v309 reconstruction gaps from real Java 11 classfile references

**Repository:** Trexzo/SpawnPK-Client  
**Parent:** R447 draft PR #1243  
**Status:** DRAFT, UNMERGED, NOT DEPLOYED. No original client runtime, private source upload, or production persistence changes.

## What was missing after R447

R447 counted class names that overlap or differ between the original v309 ZIP (10,502 class files / 419 non-class entries), the isolated R421 reconstructed output (1,394 compiled class files from 1,277 Java sources), and the two filtered legacy dependency JARs. The result identifies inventory gaps but does not reveal which absent classes are **directly referenced by recovered code**, which are available only in the alternate dependency, or which missing names could matter to a specific rebuilt entrypoint.

R448 adds a private-only **reconstruction worklist** driven by static references in the actual compiled R421 classfiles. This is a prioritized lead list for future owner-side investigation, not a claim of deobfuscated source completeness, automatic class recovery, successful linking, or runtime gameplay parity.

## Bytecode and input validation

`tools/r448/audit_rebuilt_class_linkage.py`:

- Calls R447 to require a byte-pinned original v309 `client.jar` at exact SHA256 `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38` with exactly 10,502 class ZIP entries and 419 resource entries. Neither original ZIP entry bytes nor its class code are executed.
- Calls R446 to validate only the exact isolated owner-TEMP R421 1,277-source/1,394-class trees and the two dependency JARs, including the fixed Store Java/class SHA pins. It hashes every compiled class file against R446's freshly observed SHA mapping, uses R445's bounded nofollow reads, refuses unexpected major versions other than Java 11 / classfile major 55 and rejects malformed constant pools.
- Reuses R388's `constant_class_refs` parser to extract bytecode Class constant-pool references from the reconstructed classfiles **only**. It does not load, initialize, reflect, instrument or execute the Java classes, and does not read application/cache/player history.
- Compares each observed reference with the union of the reconstructed classes and the preferred `R239_filtered.jar` class names. A reference absent from both is classified into **(a) present in original v309** or **(b) not present in that original JAR**, with an additional flag for availability in alternate `R218.jar`.
- Reports an advisory count of compiled classes lacking a matching *source filename heuristic*; inner classes can legitimately share outer sources, so this is **not** definitive ownership or a source gap.
- Optionally accepts `--entrypoint-class` for a class that must actually exist in the reconstructed class inventory. It follows only graph edges to reconstructed classes, then counts unresolved targets in that reachable subset. It does **not** claim that the selected entrypoint matches the original game's actual startup or gameplay path.
- Aggregates original resource names by extension. If R447 was also supplied an independently preserved private resource companion, it additionally reports byte-matched/missing/mismatched/extra resource counts. This is neither runtime resource loading nor proof that assets are packed into a runnable client.

An unresolved class reference can be caused by renamed/obfuscated symbols, optional code paths, descriptor-only dependencies, reflection, platform or library differences, dynamic class loading or dead code. Constant-pool Class entries are *not* a complete dependency graph. Classes present by name can still be binary-incompatible. No runtime safe assumption follows from a clean summary.

## Owner-local usage

Once the authorized owner PC is reachable and still holds the exact R421 isolated acceptance trees and original SHA-pinned v309 JAR, from the R448 GitHub checkout:

```powershell
python -B tools\r448\audit_rebuilt_class_linkage.py --original-v309-jar '<private original v309 JAR path>'
```

Optional entrypoint filter (only if that exact class exists in the reconstructed R421 class tree):

```powershell
python -B tools\r448\audit_rebuilt_class_linkage.py --original-v309-jar '<private original v309 JAR path>' --entrypoint-class 'rs/plugins/loottracker/LootHistoryStore.class'
```

Optional private diagnostic output, after **two independent read-only scans agree**:

```powershell
python -B tools\r448\audit_rebuilt_class_linkage.py --original-v309-jar '<private original v309 JAR path>' --save-private-unapproved-worklist
```

Without that explicit save flag, the tool creates **no files**, and outputs **only aggregate counts and booleans**. With the flag it creates one new unique private OS TEMP quarantine directory, never overwrites any existing file, and stores `R448-UNAPPROVED-LINKAGE-WORKLIST.json` there. The private JSON contains **class names, direct rebuilt-class referencers and prioritization counts**, not recovered source or class bytecode or the user's history. It is deliberately labeled `UNAPPROVED`; do not upload it to a public repository.

A reference is prioritized by the number of distinct rebuilt classfiles referencing it, then whether it is present as a named class in the original v309 archive. That is **investigation order**, not proof that a class should be copied from a JAR, or that a runtime loader needs that symbol.

## Evidence held open

The owner connection `DESKTOP-LTXXO4K` remains offline as of R448 intake. Hosted CI uses fabricated Java11 constant pools, fake JARs and dummy source files in temporary directories; it **cannot** run an actual private R421 audit or validate game assets. The historical independently approved full R421 manifest required by R442/R440/R425/R432 remains missing; R446 current observation cannot self-approve it. The R415–R417 persistent journal write fence, private Loot Tracker actual-code integration and EDT responsiveness also remain untested against the real client.

R448 does **not** install a JAR, modify client/assets, run SpawnPK, decompile original binaries, grant release authority, acknowledge/delete journal intent, clear history, or merge any draft PR. **Full readable source, runtime-compatible class linkage, bundled assets, login and gameplay functionality are not yet proven.**

## Public CI

Twenty-five new invented-only tests check correct Class constant-pool interpretation; missing targets present in the exact original and absent from it; alternate-only references; entrypoint-reachable ranking; Java 11 major version; tampered class bytes; invalid or truncated constant pools; bounded byte reads; resource extension grouping; companion asset coverage; negative SHA controls; optional private worklist quarantine with no overwrite; input stability on second scan; no path or class-name leaks in stdout; release flags that remain closed. Windows/Ubuntu × Python 3.11/3.13 CI also executes inherited R447/R446/R445/R444/R442/R426 public regressions. No real original v309 JAR or private Store source is committed.

**Next useful owner work**: Run R446/R447/R448 on the real isolated tree when access is restored, examine the *private* name-only worklist, and prioritize true missing classpath symbols, resource lookups and source-to-class mapping. Separately recover the historical independent R421 inventory before R425/R432 real Store admission, and audit actual plugin lifecycle before any v312 deployment.

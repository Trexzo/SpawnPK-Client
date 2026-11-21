# R454 — Rebuilt Java 11 superclass and interface member ancestry evidence

**Repository:** `Trexzo/SpawnPK-Client`  
**Parent:** R453 PR #1250, 4/4 platform CI and Recovery CI passed on `c8df314f`  
**State:** DRAFT / UNMERGED / NOT DEPLOYED.

## Scope and precise interpretation

R453 inventories JVM `CONSTANT_Fieldref`, `CONSTANT_Methodref` and `CONSTANT_InterfaceMethodref` triples from the actually rebuilt R421 classfiles, and checks whether their owner directly declares a same-name/same-descriptor member. That direct-only test intentionally leaves inherited members as unresolved.

R454 extends the **read-only** classfile metadata parser to capture `interfaces[]`, class access flags, and each declared member's JVM access flags, keeping the existing R453 API usable. It then searches reconstructed superclass and transitive interface ancestry for exact signature declarations, reporting **possible inherited matches**, not confirmed JVM resolution.

`tools/r454/member_ancestry_evidence.py` builds an offline, bounded graph of reconstructed `super_class` and `interfaces[]` links. It detects actual path cycles without falsely classifying a shared diamond-interface ancestor as cyclic. It caps paths, depth, and states. It never reads Java execution state or launches the client. It distinguishes:

- Direct member declarations on the referenced rebuilt class.
- Possible matching declarations on a reconstructed superclass.
- Possible matching declarations on a reconstructed interface, including superinterfaces and interfaces reached through parent classes.
- Ancestor signatures that cannot safely be treated as inherited: private methods/fields, static interface methods, or absent member access metadata.
- `<init>` constructors and `<clinit>` class initializers, which **are never inherited**.
- Unknown external or JDK ancestry branches where required declarations may reside outside the reconstructed class inventory.
- Member signatures missing from all currently available reconstructed ancestors, carefully **not** claiming they are absent from a real classloader.
- Cyclic, over-budget or otherwise uncertain ancestry, conservatively not counted as a verified candidate.
- Missing or unparsed original/dependency member owners are still counted separately rather than claimed resolved.

This structural matching **does not implement JVMS field/method resolution**: checks for package/protected access, static/instance compatibility, bridges/covariant return, multiple inherited default conflicts, interface specificity, runtime classpath composition or actual method invocation are absent. A matching ancestor name and descriptor is a reconstruction lead, not evidence of an accessible member or JVM linkage.

## Owner-only SHA gates

`tools/r454/audit_inherited_member_ancestry.py` first runs inherited R453→R452→R451→R450→R449→R448→R447→R446 gates. The original v309 `client.jar` must match SHA256 `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`, with exactly **10,502 classes and 419 resources**. The isolated R421 owner-TEMP source and Java 11 compiled inventories must match **1,277 Java source files / 1,394 compiled class files**, pinned `LootHistoryStore.java` and `LootHistoryStore.class` SHA values, plus the R239 and R218 dependency JAR inputs.

The audit independently re-reads and SHA-verifies every compiled Java 11 class before constructing ancestry, compares its member reference count to R453, checks the original resource archive names and both dependency archive SHA values, then reobserves the entire current owner inventory. A **current-state** observed file set is never an independently authenticated historical R421 full baseline. Original classfile bytes and source code are not copied or published.

Default stdout contains only aggregate numbers and explicit release/merge refusal flags, without private class, method, resource names, paths, hashes or JAR bytes. Optional `--resource-companion-root` checks an already present private resource companion but never packages assets.

## Owner Windows usage (when the authorized machine is available)

Default read-only aggregate inspection:

```powershell
python -B tools\r454\audit_inherited_member_ancestry.py --original-v309-jar '<owner-local exact original v309 client.jar>'
```

Explicit **private-only** worklist:

```powershell
python -B tools\r454\audit_inherited_member_ancestry.py --original-v309-jar '<owner-local original v309 client.jar>' --save-private-unapproved-worklist
```

The save flag scans all inputs twice and also requires identity of the entire current source/class/dependency SHA inventory across scans. On success, only a **new, exclusive OS TEMP folder** under the owner account is created with `R454-UNAPPROVED-MEMBER-ANCESTRY.json`. The JSON contains *names and candidate referencers*, not original code or bytes. It remains an **unapproved private worklist** and must never be uploaded to public GitHub. Existing files are not overwritten.

## Tests, remaining gaps and safety

R454 adds **36 invented Java 11 and ancestry regressions**, including raw CP interface/access flag parsing, superclass and interface hierarchies, private/static exclusions, constructors, distinct JVM descriptors, missing dependencies, cycles, diamond paths, depth budgets, source SHA races, aggregate-only output, private no-overwrite quarantine and malformed input refusal. Hosted Windows/Ubuntu × Python 3.11/3.13 CI also runs inherited R453–R445, R442 and R426 public tests. The hosted fixture data is fabricated and has no private recovered SpawnPK source.

The owner device `DESKTOP-LTXXO4K` remained offline (last seen about 136 hours ago) at R454 intake. No private original v309 JAR, R421 source, assets or production history could be inspected in this session. Historical independent R421 full inventory approval remains missing, as do real R440/R425/R432 Store acceptance, actual LootTrackerPlugin persistence integration, recompilation and asset-packed playable JAR startup. No v312 version acceptance, login, GUI, gameplay, FPS optimization or reconstruction completeness is proven.

**Keep R454 draft/unmerged. No client replacement, deployment, production account history access, R415/R417 deletion marker cleanup, persistence write unlock, or release is authorized.**

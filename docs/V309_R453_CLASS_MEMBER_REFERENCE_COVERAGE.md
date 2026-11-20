# R453 — JVM method and field reference signatures for reconstructed source mapping

**Repository:** `Trexzo/SpawnPK-Client`  
**Parent:** R452 draft PR #1249; R452 4/4 public CI passed on `40cfbbec`.  
**State:** DRAFT / UNMERGED / NOT DEPLOYED.

## Motivation

Earlier R447–R452 analyses map original v309 class names, Java 11 constant-pool `CONSTANT_Class` references, field/method descriptor types, generic Signature types, resource-like strings and bounded resource API argument dataflow. They do not inventory individual **JVM field and method references** in reconstructed compiled bytecode. An exact class name on the classpath does **not** establish that the referenced `name:descriptor` exists.

R453 adds a structured, offline method and field reference census. It parses `CONSTANT_Fieldref`, `CONSTANT_Methodref` and `CONSTANT_InterfaceMethodref` entries from every isolated R421 compiled class and compares each against *directly declared* members in reconstructed owners. The goal is a private priority worklist for resolving binary API gaps in recovered readable source. It is not compilation, deobfuscation, inherited member resolution, classloader verification or a binary compatibility guarantee.

## What it actually checks

`tools/r453/classfile_member_reference.py` is a pure Java 11 classfile parser. It rejects invalid magic/version, oversized or truncated CP entries, unsafe owner/name/descriptor strings, invalid class/NameAndType indices, wrong field-vs-method descriptor kinds, trailing classfile bytes and duplicate direct declarations. It reads owner/superclass names, directly declared fields/methods and unique Fieldref/Methodref/InterfaceMethodref owner/name/descriptor triples, never executing Java bytecode.

`tools/r453/audit_member_reference_coverage.py` classifies each CP member reference as:
- Java/JDK platform owner (**not checked**, no false missing dependency assertion).
- Reconstructed owner **directly declaring the exact name/descriptor**.
- Reconstructed owner **not directly declaring** that member. This is **not proof of a broken link**: it can be legitimately inherited, generated/bridged, or otherwise resolved.
- Preferred `R239_filtered.jar` dependency owner present. **The dependency's member bytecode is not parsed in R453**; this status is also not proof that its member exists.
- Owner absent from the reconstructed/preferred classpath, with separate advisory counts for names present in the original v309 JAR and alternate `R218.jar`.

It counts field refs, class-method refs, interface-method refs, class-source to referenced-member pairs, and distinct potentially missing owners. Normal output contains **aggregate numbers only**. The private candidate list sorts by how many reconstructed classfiles mention a member, and includes source/owner/member names and descriptors, never source code or original class bytes. All provisional labels explicitly leave inherited JVM resolution and runtime linkage unverified.

## Exact owner-only input gates

The audit first runs inherited R452→R451→R450→R449→R448→R447→R446 validation, requiring:

- Exact original v309 JAR SHA256 `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`, and exactly **10,502 classfiles / 419 resources**.
- Exact isolated owner-TEMP R421 reconstructed source/class inventory: **1,277 Java source files / 1,394 compiled Java 11 class files**, fixed LootHistoryStore Java and class SHA fingerprints, and the two filtered dependency ZIPs.
- SHA256 validation of every observed compiled class before member extraction and full original/dependency/read-only current inventory rechecks afterward. No classloader or client launch is involved, and the original JAR is used only for central-directory class-name evidence.
- At no point does the audit self-create or approve the independently established historical R421 full baseline required by R442/R440/R425/R432. Reobserving *current* files is not historical provenance.

Optional `--resource-companion-root` retains inherited read-only resource byte comparison but does not package or install assets.

## Owner-side use (once available)

Read-only aggregate check from R453 checkout on the authorized Windows computer:

```powershell
python -B tools\r453\audit_member_reference_coverage.py --original-v309-jar '<owner-local exact v309 client.jar>'
```

To explicitly write a **new owner-only private TEMP** worklist:

```powershell
python -B tools\r453\audit_member_reference_coverage.py --original-v309-jar '<owner-local exact v309 client.jar>' --save-private-unapproved-worklist
```

The private flag requires two full identical audits and identical **whole source/class/dependency SHA inventories** before a fresh exclusive new `R453-UNAPPROVED-MEMBER-REFERENCE-WORKLIST.json` is created in a unique owner OS TEMP folder. The saved JSON contains only *names, descriptors and referencer identities* and explicit non-approval flags. It must stay private; do **not** upload it to GitHub. Existing reports are never overwritten.

## Public validation and remaining gaps

The public CI uses invented Java 11 classes, fake original JARs, invented owner-TEMP reconstructed trees and only source-free synthetic tests: **26 new R453 regression tests**, plus inherited R452–R445, R442, R426 on Windows/Ubuntu × Python 3.11/3.13. No actual SpawnPK binaries, recovered private source or player histories enter GitHub CI.

This is **not** JVM member linkage or subclass resolution. A method not declared on its immediate class may be inherited; a member name declared on a class does not prove it is accessible, compatible, invoked, present in dynamic runtime dependencies, or equivalent to obfuscated original v309. Interface defaults, covariant signatures, access flags, protected/private fields, invokedynamic/bootstrap method handles and native JNI are not resolved. R453 does not recover additional original source or assets, execute the client, replace client.jar, verify v312, validate GUI/login/gameplay/FPS, or fix production async persistence. Owner `DESKTOP-LTXXO4K` remains offline; the historical approved R421 full source/class inventory is still missing.

**Keep this draft/unmerged; no production history access, R415/R417 deletion intent or acknowledgment marker cleanup, write unlock, client installation, or release is authorized.**

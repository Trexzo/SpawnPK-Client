# R449 — Java 11 descriptor-only class gaps and possible resource string references

**Repository:** `Trexzo/SpawnPK-Client`  
**Parent:** R448 draft PR #1244  
**State:** DRAFT / UNMERGED / NOT DEPLOYED.

## Scope

R447 provides original v309 JAR class/resource coverage; R448 extracts `CONSTANT_Class` references from the **actually reconstructed R421 Java 11 classfiles**. Some referenced types do **not** appear as `CONSTANT_Class` entries: they can be present in a field descriptor (`Lrs/Thing;`), method descriptor (`(Lrs/A;[Lrs/B;)V`), a `CONSTANT_NameAndType` descriptor, or a `CONSTANT_MethodType` descriptor. Also, some asset filenames occur as Java `CONSTANT_String` entries and can be investigated against the original JAR's 419 non-class resources.

R449 adds a bounded read-only binary parser for this material. The intent is to identify **additional owner-private reconstruction leads**, not to claim real linking or resource usage. The worklist explicitly excludes dynamic reflection, JNI, generic signatures and most runtime-generated filenames. A constant-pool string that resembles a resource path **does not prove a file-loading call**, and the presence of a class name does not prove JVM binary compatibility.

## Input and admission

`tools/r449/audit_descriptor_resource_gaps.py` first calls R448 (and its inherited R447/R446 gates). Therefore all owner-local analysis still requires:

- Original v309 client JAR SHA256 `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`, exactly **10,502 class files** and **419 non-class resources**, with ZIP path/duplicate/symlink/size checks.
- Exact historical R421 owner-TEMP isolated roots with **1,277 reconstructed Java sources** and **1,394 compiled classes**, each currently observed SHA. The hard-pinned `LootHistoryStore.java` and `LootHistoryStore.class` SHA values must match. Only two filtered dependency JARs are read, not executed.
- Read-only bounded nofollow owner file access from R445; the R449 graph checks every individual compiled-class SHA and classfile major **55** (Java 11) a second time. Inputs are observed again before the result is accepted. This is a current-state stability check, **not an independently approved older baseline**.

## Static inspection and resulting aggregates

R449 reads constant-pool structures and the metadata portion of each compiled classfile, including declared fields/methods. It recognizes valid Java field/method descriptors, object and array types, primitive types, and `CONSTANT_NameAndType`/`CONSTANT_MethodType` entries. It fails closed on malformed/truncated descriptors, unsafe class paths, invalid constant-pool references and unexpected trailing bytes. UTF-8 constants are never executed.

Descriptor targets already found through *any* recovered classfile's R448 `CONSTANT_Class` entries are removed from the **incremental** descriptor-only tally. Remaining non-platform target names are compared against:
- reconstructed compiled class names plus preferred `R239_filtered.jar`;
- original v309 class names; and
- alternate `R218.jar` class names.

Java string constants are separately filtered for plausible archive-relative filenames with common resource extensions, including PNG/images, JSON, fonts, text, metadata and shader files. Dangerous relative paths, URL schemes and Windows drives are excluded. The program reports how many resource-like strings are named in the original JAR and how many are not. These are **candidates, not proven resource loads**.

**Normal stdout contains aggregate counts and nonapproval flags only**; it never emits private class names, source filenames, asset paths, individual hashes, original class bytecode or local paths. Optionally, `--resource-companion-root` invokes the inherited R447 byte comparison against a **preexisting** private resource companion but does not package or install it.

## Owner-side commands

From the appropriate R449 checkout on the owner Windows machine, after verifying access to the exact isolated R421 compiled tree:

```powershell
python -B tools\r449\audit_descriptor_resource_gaps.py --original-v309-jar '<owner-local SHA-pinned original JAR>'
```

To compare a previously preserved 419-resource private companion as well:

```powershell
python -B tools\r449\audit_descriptor_resource_gaps.py --original-v309-jar '<owner-local SHA-pinned original JAR>' --resource-companion-root '<private, already existing resource companion>'
```

An optional explicit `--save-private-unapproved-worklist` repeats the entire audit and, only if the full report and worklist agree, creates **one new**, exclusive-output directory under owner OS TEMP holding `R449-UNAPPROVED-DESCRIPTORS-AND-RESOURCES.json`. That private JSON contains new descriptor-only class names with their referencing recovered class names, plus possible resource filenames and source-class referencers. No original Java source, compiled bytes or JAR is copied. **Do not upload the report to public GitHub.**

```powershell
python -B tools\r449\audit_descriptor_resource_gaps.py --original-v309-jar '<owner-local SHA-pinned original JAR>' --save-private-unapproved-worklist
```

## What remains unresolved

No source or class execution, client startup, user history inspection, actual resource loading, Java GUI/Swing, login, original JVM instruction parity, dynamic classloading, generic signatures or real v312 restart acceptance is performed. A dynamic Java string may not be present as `CONSTANT_String`; generic `Signature` type references, complex annotations and other classfile attributes are not yet covered. A descriptor-only missing name can be renamed, optional, or unreachable in gameplay.

The owner PC `DESKTOP-LTXXO4K` remains offline at R449 intake. All **27 new synthetic tests** use invented Java11 classfiles and temporary dummy ZIP/resource trees, not actual owner-private R421 classes or v309 JAR bytes. Windows/Ubuntu × Python 3.11/3.13 CI also runs inherited R448→R444, R442 and R426 tests. Real R421 full historical independent SHA approval required by R442/R440/R425/R432 is still missing; a present-day observation cannot self-approve it. Real Loot Tracker async Store/Plugin integration, source+asset complete JAR build and runtime correctness remain unverified.

**No branch merge, JAR installation, private source distribution, player history or R415/R417 journal deletion, write unlock, or deployment is authorized.**

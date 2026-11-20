# R450 — Generic Java signatures and bytecode-local resource API proximity

**Repository:** `Trexzo/SpawnPK-Client`  
**Parent:** R449 draft PR #1245  
**Status:** DRAFT / UNMERGED / NOT DEPLOYED. Original client and source unavailable in hosted CI.

## Why R450 matters to full client reconstruction

R448 identified class `CONSTANT_Class` references in the reconstructed Java 11 output. R449 added field/method descriptors, `CONSTANT_NameAndType` and `CONSTANT_MethodType`, plus a candidate list of resource-like `CONSTANT_String` entries. Two important static gaps remained:

1. Generic Java `Signature` attributes refer to class types that can be absent from both the `CONSTANT_Class` index and ordinary field/method descriptors, including nested type arguments, type bounds, and declared generic throws. Such types are not necessarily loaded by a JVM at runtime, but are useful for reconstructing type-level architecture and readable source.
2. An asset-like string in the constant pool may be unrelated to resource loading. A stronger, still advisory signal is a `ldc`/`ldc_w` resource-like string **within 96 bytes before** a recognized `Class` or `ClassLoader` `getResource*` invocation in the **same method's parsed bytecode**. This is proximity only: branches, exception paths, the operand stack, and dynamic names are not tracked. It does not prove the string is an invocation argument, a resource is actually loaded, or that a method executes.

## Code and safeguards

`tools/r450/classfile_signature_resource.py` provides a bounded, pure byte parser, with no filesystem access. It parses class, method and field `Signature` attributes using the Java generic-signature grammar: array/reference types, type variables, class type parameters and wildcards, nested inner classes, generic interfaces/superclasses, generic method returns and throws. It canonicalizes generic inner segments to binary `$` class-name form and rejects malformed, truncated or excessive nesting and untrusted filenames.

It also parses bounded Java 11 classfile `Code` attributes and opcode boundaries (including switch alignment, `wide`, `ldc_w` and invokes), rather than naively searching raw bytes. It only counts a string as a stronger resource candidate when a known, exactly named resource API invocation and string literal occur within the same parsed method with the literal earlier and nearby. Dynamic loading/reflection, unsupported type annotation metadata, third-party library asset APIs and control-flow/data-flow are explicitly **not** proven.

`tools/r450/audit_generic_resource_proximity.py` integrates the pure parser with the existing read-only gates: R449→R448→R447→R446. It requires the original v309 JAR SHA256 `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`, exactly **10,502 original class files** and **419 original non-class resources**, the exact isolated owner-TEMP R421 root with **1,277 reconstructed Java sources** and **1,394 Java 11 compiled classes**, SHA-pinned original `LootHistoryStore.java` / `LootHistoryStore.class`, and both filtered dependency JARs. It compares observed individual classfile SHA256 against the current full inventory and refuses changes. R450 then re-observes inputs; this is **present-day consistency, not historically authenticated provenance**.

Results are aggregate **counts only** by default: new generic class names not previously recognized by R449, unresolved generic class targets present/absent in the exact original v309 class list, alternate-dependency availability, known resource API invocation count, possible resource strings within method-code proximity, and how many match original resource paths. It does not print private class names, method names, resource filenames or SHA values.

Optionally, `--resource-companion-root` retains R447's byte-for-byte check of a separately existing **private original resource companion**, which does **not** prove those files are packaged in a rebuilt client.

## Owner-only usage when machine becomes available

From the checkout on the authorized owner PC:

```powershell
python -B tools\r450\audit_generic_resource_proximity.py --original-v309-jar '<owner-local exact original v309 client.jar>'
```

To create a detailed private worklist of name-only generic gaps and bytecode-local resource leads, **explicitly opt in**:

```powershell
python -B tools\r450\audit_generic_resource_proximity.py --original-v309-jar '<owner-local exact original v309 client.jar>' --save-private-unapproved-worklist
```

The save flag performs the entire read-only audit **again**, rejects changed summaries or detailed worklists, and creates one **new** uniquely named owner-private TEMP quarantine directory containing `R450-UNAPPROVED-GENERIC-RESOURCE-WORKLIST.json`. No old file is overwritten and no source/class bytes are copied. The report is deliberately marked `UNAPPROVED`, never an R442 historical full-inventory baseline. Do **not** upload private worklists to public GitHub.

## Limits and next real gate

This workflow does not compile Java, reconstruct missing classes, launch or log into SpawnPK, run gameplay, verify GUI behavior, test FPS gains, resolve v312 compatibility, package assets, or modify the installed client. It does not reconcile or remove persistent R415/R417 deletion markers and does not open player history, settings, credentials or caches. It does not establish instruction-level JVM parity. The independent historical approved R421 whole-tree reference needed for owner-local R440/R425/R432 acceptance remains missing.

The owner device `DESKTOP-LTXXO4K` is currently offline. Hosted Windows/Ubuntu × Python 3.11/3.13 CI runs 26 fabricated Java 11 generic signature and bytecode tests, fake JARs and isolated temporary files, plus inherited R449→R444, R442 and R426 public regression suites. **No actual owner-private R421 files or pinned original client bytes enter hosted CI**.

A future iteration can analyze annotation Signature data and perform bounded bytecode operand-stack tracking for resource calls, but should not call static string proximity confirmed loading. Reconstructing a complete, deobfuscated, runnable source tree with all 419 original resources requires real private owner-local evidence and separate build+runtime acceptance.

**Keep this PR DRAFT/UNMERGED. No production history writes, journal intent deletion, write unlock, client replacement or deployment are authorized.**

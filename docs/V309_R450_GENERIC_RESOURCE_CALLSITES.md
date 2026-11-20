# R450 — Generic Java signatures and adjacent resource-loader callsite evidence

**Repository:** Trexzo/SpawnPK-Client. **Parent:** R449 draft PR #1245. **DRAFT, UNMERGED, NOT DEPLOYED.**

## New reconstruction coverage

R449 recognized class references in declared field/method descriptors, CONSTANT_NameAndType and CONSTANT_MethodType, plus all resource-looking CONSTANT_String literals. The earlier R448 scanner recognized CONSTANT_Class references. Neither parses generic `Signature` attributes that can name additional original v309 classes, and a filename-like string on its own cannot tell us whether a method actually contains a resource loader invocation.

R450 implements `tools/r450/audit_generic_signatures_resource_calls.py` with two new analyses:

1. A bounded grammar parser for Java 11 generic **class, field, and method Signature attributes**, including type parameters and bounds, nested generics, arrays, wildcard type arguments, class-inner segments, method results and declared throws. It identifies *incremental class names* missing from **all** earlier R449 Class+descriptor references, and counts those unresolved by the reconstructed R421 classes plus preferred dependency, their presence in original v309, and whether the alternate dependency contains the class.
2. A strictly bounded Java `Code` attribute instruction parser that recognizes **immediately adjacent `ldc` or `ldc_w` of a CONSTANT_String** and `invokevirtual` or `invokestatic` of a correctly typed, exact-signature `java/lang/Class` or `java/lang/ClassLoader` resource getter. The callsite candidate reports loader owner/name and filename only in the optional owner-private report. The aggregate stdout counts possible direct callsites and resource paths present/absent from the SHA-verified original JAR's 419 resource entries.

Supported loader methods are `Class.getResource`, `Class.getResourceAsStream`, `ClassLoader.getResource`, `ClassLoader.getResourceAsStream`, `ClassLoader.getSystemResource` and `ClassLoader.getSystemResourceAsStream` with exact string argument and URL/InputStream return descriptors. This deliberately narrow pattern avoids claiming every resource-like literal is an actual load. More complex sequences such as `getClass().getResource(name)` where there are multiple intermediate JVM instructions, or resource URLs built dynamically, may not be counted. Even an adjacent literal/call pair is **not data-flow or execution proof**: dead code, exception paths, stack behavior and runtime classloaders are not resolved.

The classfile reader validates constant-pool indices, attribute boundaries, Signature contexts, Java11 classfile major 55, Code lengths, instruction lengths and switch/wide forms, within strict read/syntax/count limits. Malformed descriptors, invalid generic signatures, unsafe paths, unsupported bytecode tags and altered input files fail closed. It neither patches nor initializes classes.

## Hard input gates and privacy

The tool calls R449 then independently reads/validates the exact R421 isolated owner-TEMP source/class trees using R446, including **1,277 Java sources, 1,394 compiled classes**, known `LootHistoryStore` source/class SHA pins, and the two filtered dependency ZIPs. It requires R447's byte-pinned original v309 JAR with SHA256 `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`, exactly **10,502 class entries and 419 resources**, and refuses changing class/JAR input between read-only passes. No client is launched and no private source code or original JAR/class/resource bytes are copied to GitHub.

The default output is **aggregate counts and nonapproval flags only**—not private filenames, raw hashes, class bytes or paths. The optional `--save-private-unapproved-worklist` flag independently repeats the full audit and, only if outputs match, writes an exclusively created **new owner-private OS TEMP quarantine** file. It includes incremental generic type names and adjacent loader-callsite filenames with referencing class names; it remains an `UNAPPROVED` worklist, not deployable code or a historical approved manifest.

### Owner-side read-only usage

From the R450 GitHub checkout on the authorized owner Windows PC, once its preserved R421 isolated TEMP roots are available:

```powershell
python -B tools\r450\audit_generic_signatures_resource_calls.py --original-v309-jar '<owner-local SHA-pinned original v309 JAR>'
```

Optional byte comparison with an **already present** private 419-resource companion:

```powershell
python -B tools\r450\audit_generic_signatures_resource_calls.py --original-v309-jar '<owner-local SHA-pinned original v309 JAR>' --resource-companion-root '<already existing private companion>'
```

To save the private, explicitly unapproved names-only diagnostic in a unique new TEMP folder:

```powershell
python -B tools\r450\audit_generic_signatures_resource_calls.py --original-v309-jar '<owner-local SHA-pinned original v309 JAR>' --save-private-unapproved-worklist
```

Do **not** upload private source, compiled class/JAR data, or the local mapping file to a public repository. No data is written when the save flag is absent.

## Verification and unchanged blockers

27 fabricated Java11 classfile/ZIP/TEMP regressions check nested generic type grammar, bounds, throws, wildcards, descriptor differences, adjacent loader callsites, negative decoy loaders and non-adjacent literals, instruction length/wide/switch parsing, invalid/truncated classfiles, per-member SHA drift, aggregate-only output, explicit private output no-overwrite, and zero-release assertions. Windows/Ubuntu × Python3.11/3.13 GitHub CI runs these plus inherited R449–R445, R442 and R426 suites. **Public CI receives invented classes only, not actual owner R421 or original v309 binaries.**

Owner device `DESKTOP-LTXXO4K` was offline at intake. The historical independently approved **full R421 source/class inventory** still has not been recovered. Actual owner-private R442/R440/R425/R432 acceptance, source deobfuscation completeness, resource bundling, Swing EDT tests, login/gameplay and v312 runtime behavior remain **unverified**. Neither generic signatures nor adjacent callsite patterns prove JVM linkability or application function.

R415/R417 persistence intent/ack write fences remain unchanged. **No merge, private-source release, live client installation, history deletion, journal cleanup or write unlocking is authorized.**

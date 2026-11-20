# R451 — Conservative straight-line JVM resource String-operand attribution

**Repository:** `Trexzo/SpawnPK-Client`  
**Parent:** R450 PR #1247, all 4 public CI jobs passed  
**Status:** DRAFT, UNMERGED, NOT DEPLOYED.

## Motivation

R450 detects resource-like `CONSTANT_String` values loaded shortly before allowlisted `Class.getResource*` / `ClassLoader.getResource*` calls in the **same method**. Such proximity can produce misleading candidates if the string is popped, overwritten, placed in a different argument position, or never reaches the invocation.

R451 adds a *narrow* symbolic JVM operand stack tracker for **fully modeled, straight-line Java 11 method bodies**. It identifies when a literal `String` is actually present in the invocation argument slot under that limited static model, rather than nearby in bytes. This improves static reconstruction worklists but is not JVM verification, dynamic dataflow, execution or proof of a successful resource load.

## Implementation

`tools/r450/classfile_signature_resource.py` now supports an **optional read-only code observer callback**, preserving its original return format and R450 tests when absent. The callback receives one decoded method's bytecode and maximum stack/locals, exception count, and typed constant-pool String/method reference resolver functions. It never executes a method or receives filesystem paths.

`tools/r451/straightline_resource_operands.py` handles a deliberately small instruction subset:
- `ldc` and `ldc_w` actual `CONSTANT_String` constants, reference local `aload*` / `astore*`, `aload_0`, null and selected primitive constants.
- `pop`, `dup`, `swap`, `checkcast`, and modeled JVM method calls. It consumes the correct receiver and method parameters for known, parsed invocation descriptors and pushes unknown return values.
- At an allowlisted resource API invocation, the top method parameter must symbolically be a literal `String` read from a real `CONSTANT_String`; arbitrary `CONSTANT_Utf8` values cannot be promoted to arguments. Static `ClassLoader.getSystemResource*` calls are supported without a receiver.
- Entire methods are excluded from attributable output when they contain branches/switches/exception handlers, any unmodeled opcode, an unmodeled category-two `long`/`double` value, an empty operand stack, excessive locals/stack/calls, or any other uncertain JVM stack effect. Such a method contributes **no proven-argument candidates**, even if earlier instructions looked convincing. Unknown source expressions and dynamically produced strings also stay unknown.

`tools/r451/audit_resource_operand_arguments.py` inherits R450→R449→R448→R447→R446 owner-only admission:
- Exactly SHA-pinned original v309 `client.jar`, SHA256 `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`, 10,502 classes and 419 original non-class resources.
- Exact owner-isolated R421 current tree with 1,277 Java source files and 1,394 compiled class files, original `LootHistoryStore.java`/`.class` pins, stable per-file SHA observation, and R239/R218 dependency JAR checks. The current observation is **not an independently approved historical R421 reference**.
- Counts resource API calls observed; counts call instructions within **fully modeled** methods; counts static literal argument occurrences and how many candidate resource filenames exist in the original JAR; and counts R450 proximity pairs that were not established as literal operands by the straight-line model.
- No private class, source, method or resource filename, paths, hash values, Java code, player history or per-file inventory is printed to stdout.

### Owner-only usage

After the authorized owner device reconnects, run from its checkout (read-only default):

```powershell
python -B tools\r451\audit_resource_operand_arguments.py --original-v309-jar '<owner-local exact original v309 JAR>'
```

An optional `--resource-companion-root` invokes inherited SHA byte comparisons against an **already existing** isolated private resource companion. This does **not** package a playable client.

The explicit `--save-private-unapproved-worklist` option repeats the complete audit and only when both reports agree creates one **new**, exclusive, owner-TEMP quarantine file `R451-UNAPPROVED-RESOURCE-ARGUMENT-WORKLIST.json`. The private report contains only class/method/resource *names*, explanatory booleans and per-method candidate/refusal summaries; never recovered source, bytecode, or player histories. Do not upload private worklists into public GitHub.

## Limits: no runtime certainty

This symbolic model excludes branching, exceptions and unmodeled instructions. The resulting count is a **lower-bound on static literal-argument evidence in analyzed code**, not a census of every actual load or proof of the invoked resource at runtime. It does not model virtual dispatch, resource lookup rules/classloader resolution, runtime reachability, reflection, JNI, Java signatures beyond prior R450 coverage, or all JVM bytecodes. Presence of a filename in an original JAR does not establish a complete runnable reconstructed JAR.

The original private JAR, private Store source/class, original assets, actual v312 startup, login, rendering/Swing, FPS and player history were **not accessed in hosted CI**. Owner PC `DESKTOP-LTXXO4K` remains offline. R442 independently approved historical full R421 inventory, R440/R425/R432 actual Store compile/acceptance, and R427–R431 actual async persistence integration are still pending. R415/R417 deletion-intent and acknowledgment markers remain untouched and writes stay fenced.

Public tests use invented Java 11 bytecode/ZIPs only. The Windows/Ubuntu × Python 3.11/3.13 matrix runs **32 new synthetic tests** plus inherited R450–R445, R442 and R426 suites; all are offline.

**Do not merge or install. No live JAR changes, production history reads/writes, journal cleanup, write unlock, or release authorized.**

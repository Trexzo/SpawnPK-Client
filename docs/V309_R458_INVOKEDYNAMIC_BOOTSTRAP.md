# R458 — Java 11 invokedynamic, BootstrapMethods, MethodHandle and ConstantDynamic mapping

**Repository:** `Trexzo/SpawnPK-Client`  
**Parent:** R457 draft PR #1254, verified 4/4 synthetic CI on `7ec02ea8`  
**State:** DRAFT / UNMERGED / NO DEPLOYMENT.

## Actual gap addressed

R456–R457 inspect real `getfield`, `putfield`, `invokevirtual`, `invokestatic`, `invokespecial`, `invokeinterface` and other direct Java11 `Code` instruction sites, with bounded member declarations, ancestry, preferred dependency signatures, argument-slot and constructor syntax. `invokedynamic` was only **counted as unresolved**, omitting the synthetic call site's `BootstrapMethods` method handle, its bootstrap arguments and lambda implementation method handles. Java 11 also supports dynamically computed `CONSTANT_Dynamic` constants accessed with `ldc` instructions.

R458 statically reads this missing metadata. **It never executes Java code, calls a bootstrap method or proves that a `CallSite` or dynamically computed constant resolves.**

`tools/r458/bootstrap_callsite_evidence.py` is a strict, bounded Java11 classfile parser for:
- `CONSTANT_MethodHandle` kind 1–9, with field-vs-method/interface CP tag constraints, constructor-only `REF_newInvokeSpecial` and never-constructor/initializer rules for other method handles.
- `CONSTANT_MethodType` descriptors (using R457's slot-aware grammar).
- `CONSTANT_InvokeDynamic` and `CONSTANT_Dynamic` CP entries and their exact `BootstrapMethods` table indexes and name/descriptors. Missing/out-of-range bootstrap table indexes, duplicate attributes, bad references, truncation, wrong CP tags and unbounded entries are refused before any evidence is accepted.
- Each bootstrap's `REF_invokeStatic` or `REF_newInvokeSpecial` target handle and typed, loadable bootstrap arguments. When a bootstrap argument is itself a `MethodHandle` (e.g. a lambda's implementation target), its owner/member/descriptor/kind is recorded for owner-private reconstruction. Bootstrap arguments that are other `CONSTANT_Dynamic` values are recognized but not recursively resolved or executed.
- Actual `invokedynamic` bytecode instructions (opcode `0xba`, reserved trailing operand bytes exactly zero) and `ldc`/`ldc_w`/`ldc2_w` for `CONSTANT_Dynamic`. One-slot vs two-slot constants are distinguished. **Unused CP entries do not count as executed or syntactically present instruction sites.**
- Total bootstrap and Code budgets prevent excessive parsing: 8,192 bootstrap records per class, 8,192 arguments per record, 32,768 total arguments per class, 50,000 dynamic instruction sites per class, and existing 16 MiB attribute and 32 MiB classfile caps.

The count of `invokedynamic` Code instructions must match R457's separately decoded `invokedynamic` count, on the same SHA-pinned rebuilt Java11 source tree. The report classifies bootstrap and implementation method handle owners by **name-only** classpath presence: JDK/platform, rebuilt R421, preferred R239, alternate R218, original v309 only, or absent. Known bootstrap **names** `LambdaMetafactory.metafactory/altMetafactory` and `StringConcatFactory` are counted as *hints*, not proof of generated lambdas or string concatenation. Missing owner names and unsupported dynamic dependencies are advisory reconstruction leads.

## Owner-only custody and reporting

`tools/r458/audit_bootstrap_evidence.py` inherits full R457→R446 gates:
- Exact original v309 JAR SHA256 `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38` with 10,502 original classes / 419 original resources.
- Isolated owner-TEMP R421 current source/class inventory, 1,277 Java sources and 1,394 Java11 compiled classfiles, fixed `LootHistoryStore.java` / `LootHistoryStore.class` SHA pins and the R239/R218 dependency JAR input hashes.
- Individual SHA check on every re-opened class, bounded Code/CP/attribute parse, original and dependency archive SHA/ZIP verification and a full current owner source/class/dependency inventory recheck.
- Default stdout **only aggregate numbers** and explicit nonapproval flags; no private original/client paths, class names, method names, source or original classfile bytes are printed.
- With `--save-private-unapproved-worklist` explicitly set, the *entire* scan runs twice; private report details and the full current source/class/dependency SHA inventories must match, then a new exclusive owner OS TEMP `R458-UNAPPROVED-INVOKEDYNAMIC-BOOTSTRAP.json` name-only worklist is written. Earlier reports are never overwritten; no private data is uploaded to GitHub.

Run the read-only audit only on the authorized owner Windows machine once accessible:

```powershell
python -B tools\r458\audit_bootstrap_evidence.py --original-v309-jar '<owner-local pinned original v309 JAR>'
```

To save the private unapproved name/handle/PC worklist, append `--save-private-unapproved-worklist`. The optional `--resource-companion-root` retains inherited read-only original resource comparison, **not** proof of an assembled resource-complete client.

## Public verification and remaining limitations

Public CI runs **39 invented synthetic tests** for valid lambda-like bootstrap metadata, direct method-handle implementation arguments, unused CP entries, valid dynamic constants, category-two `ldc2_w`, bad handles, missing or duplicate bootstrap tables, unencodable/malformed references and inputs, owner-private output integrity and SHA refusal. Windows/Ubuntu × Python 3.11/3.13, plus inherited R457–R445, R442 and R426 synthetic suites. Hosted CI does not possess the user's original client, private source/assets or saved history.

**Critical unverified areas:** Bootstrap argument type compatibility, recursive dynamic constant resolution/cycles, `LambdaMetafactory` runtime behavior, method handle access checks, real JVM verification/classloader resolution, live client startup, full readable original-source mapping, asset-packed runnable JAR, GUI/login, gameplay and v312 compatibility. The authorized owner desktop `DESKTOP-LTXXO4K` remained offline. The *independently approved historical* R421 full source/class inventory remains missing and cannot be reconstructed merely by taking a fresh hash list of current files.

**Keep R458 draft/unmerged. No production client replacement, player-history access, R415/R417 deletion-intent marker cleanup, write-fence bypass, or release is authorized.**

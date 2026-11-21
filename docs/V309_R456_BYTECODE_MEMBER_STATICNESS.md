# R456 — Java 11 instruction-level member opcode and staticness evidence

**Repo:** `Trexzo/SpawnPK-Client`  
**Parent:** verified R455 draft PR #1252 (4/4 synthetic CI passes).  
**Status:** DRAFT / UNMERGED / NOT DEPLOYED.

## Gap addressed

R453 inventories classfile constant-pool field/method references, R454 searches rebuilt ancestry and R455 inspects selected preferred-dependency member declarations. A `CONSTANT_Methodref` or `CONSTANT_Fieldref` can exist **without any instruction ever using it**, and member declarations may be static while client code attempts an instance invocation or field access.

R456 adds a **read-only static instruction-site inventory** for actual `getstatic`, `putstatic`, `getfield`, `putfield`, `invokevirtual`, `invokespecial`, `invokestatic` and `invokeinterface` opcodes found in exact reconstructed Java11 `Code` attributes. These are syntactically observed bytecode instructions, **not evidence they execute**. `invokedynamic` is counted as unresolved instead of manufacturing a method owner.

For each supported field or invoke instruction the reader resolves its exact constant-pool typed `Fieldref`/`Methodref`/`InterfaceMethodref` (not arbitrary UTF8 or unused references). It refuses field/method tag mismatches, `invokevirtual` pointing at interface CP references, `invokeinterface` pointed at class method references, malformed instruction lengths and invalid required `invokeinterface` operand bytes. `invokestatic`/`invokespecial` legitimately accept interface method references under Java 8+ rules.

The member declaration static bit is then compared against the operation:
- `getstatic` / `putstatic` need a static field; `getfield` / `putfield` need an instance field.
- `invokestatic` needs a static method; `invokevirtual`, `invokeinterface` and `invokespecial` need an instance method under the tested structural model.
- Exact direct declarations in rebuilt or selected preferred dependency classes are distinguished from possible inherited declarations in available ancestors; multiple providers, missing ancestry, or absent flags are **uncertain**, not considered confirmed missing APIs.
- Interface invoke-kind and `<init>`/`<clinit>` special-method uncertainties are separate.
- Visibility signals inherit R455's partial public/private/protected/package-access analysis; package, nestmate, module, protected receiver and classloader checks are NOT fully modeled.

A staticness conflict is a high-priority *static reconstruction lead*. It is **not proven to cause `IncompatibleClassChangeError`**: instructions can be unreachable, binary resolution can select other declarations, actual classloading differs, the original source may differ, and production execution has not been tested.

## Implementation

`tools/r450/classfile_signature_resource.py` gains an optional `member_observer` callback and a typed CP-member resolver. With the observer omitted, R450–R455 behavior is unchanged.

`tools/r456/member_opcode_evidence.py` decodes real Java11 Code instruction boundaries through R450's bounded parser, resolves typed member refs, enforces Fieldref/Methodref/InterfaceMethodref opcode distinctions, compares exact declaration static/instance flags, and produces aggregate counts plus owner-private name-only suspects. `invokedynamic` is counted separately, without assuming its bootstrap target. The parser does **not** perform full verifier, reachability or operand-stack analysis for general invocations.

`tools/r456/audit_member_opcode_staticness.py` inherits strict owner-source gates R455→R454→R453→R452→R451→R450→R449→R448→R447→R446:
- Original pinned v309 client SHA256 `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`, 10,502 original class files and 419 original resources.
- Owner-isolated R421 current 1,277 Java sources / 1,394 compiled Java11 classes, SHA-pinned LootHistoryStore.java/class, exact preferred/alternate JAR inputs. Re-open every class from the fixed current inventory, check its individual SHA, and safely select only referenced preferred JAR class/ancestor metadata.
- Exact per-dependency SHA and R447 ZIP admission, whole present-day owner source/class/dependency inventory rechecks, and original v309 SHA re-read. **These are current-state checks, not the missing historically approved R421 full baseline.**
- Default stdout contains aggregate counts only, no original class names, private paths, source, resource filenames, decompiled material or hashes.

With `--save-private-unapproved-worklist` the tool re-runs the complete analysis and compares the exact full current inventory and private detail report before writing one **new exclusive owner OS TEMP** folder containing `R456-UNAPPROVED-OPCODE-MEMBER-CANDIDATES.json`. Names and method/PC candidates are kept owner-private; no original bytecode, JAR, private source or history is uploaded.

### Owner-only command

```powershell
python -B tools\r456\audit_member_opcode_staticness.py --original-v309-jar '<owner-local exact original v309 JAR>'
```

Optional private worklist: append `--save-private-unapproved-worklist`. Optional `--resource-companion-root` invokes inherited byte verification on an *already available private* resource companion, but does not package or install it.

## CI and critical limitations

The public matrix uses **38 fabricated Java11 instruction/declaration tests**, plus inherited R455–R445, R442 and R426 checks, across Windows/Ubuntu and Python 3.11/3.13. No real SpawnPK client, source, private original JAR, assets or player histories are present in GitHub CI.

The owner PC `DESKTOP-LTXXO4K` remained offline during development. No real R421 classes or pinned original v309 JAR were actually audited. Java source reconstruction completeness, native interfaces, full asset packaging, v312 startup/login/GUI, gameplay, performance, true JVM member resolution, and the historic independent full R421 inventory are all **unverified**.

**Keep draft/unmerged. No production client replacement, player-history reads/writes, LootTrackerPlugin async persistence enabling, R415/R417 deletion-intent marker cleanup, write unlock, or release authorized.**

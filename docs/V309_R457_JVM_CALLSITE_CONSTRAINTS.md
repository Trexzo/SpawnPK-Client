# R457 — JVM invocation argument slot and special-method syntax evidence

**Repository:** `Trexzo/SpawnPK-Client`  
**Parent:** R456 PR #1253 (4/4 Windows/Ubuntu CI passed); separate inherited R450/R451 CI also passed at intake.  
**Status:** DRAFT / UNMERGED / NO DEPLOYMENT.

## Goal and actual change

R456 improved the rebuilt client's binary linkage audit by observing real `Code` instructions for `getstatic`, `putstatic`, `getfield`, `putfield`, `invokevirtual`, `invokespecial`, `invokestatic` and `invokeinterface`, instead of treating all constant-pool members as used. It compares each operation's static/instance expectation against direct or possible inherited declarations in the rebuilt Java 11 class tree and selected preferred dependency class metadata. However, R456 only checked that `invokeinterface`'s encoded argument-count byte was nonzero.

R457 tightens syntactic validation without performing general JVM verification:

- The additive `interface_encoded_count` field in `tools/r456/member_opcode_evidence.py` preserves the **actual unsigned JVM `invokeinterface` count operand**. Existing six-field R456 synthetic fixtures and R456's original outputs remain compatible. No bytecode is executed.
- `tools/r457/jvm_callsite_constraints.py` parses full JVM method descriptors into parameter counts, **parameter slot counts** and return width: `J`/`D` consume **two** argument slots, all Java array/reference types consume **one**. It refuses malformed, non-ASCII, oversized, trailing, unsafe object-path, more than 255 array dimensions and excessive argument-slot descriptors. `invokeinterface` expects **one receiver slot plus exactly those parameter slots**; mismatches and >255 unencodable counts become explicit audit leads. An unavailable encoded operand stays *unknown*, not verified.
- `<init>` constructors must be referenced via **`invokespecial`**, via a **class `CONSTANT_Methodref`** rather than `CONSTANT_InterfaceMethodref`, with a **void-return descriptor**. `<clinit>` must **not** appear in explicit invocation instructions. Valid `invokespecial` calls to other methods are not indiscriminately flagged.
- When the actual referenced owner is among parsed rebuilt or selected dependency classes, compare `CONSTANT_Methodref` with known **class** metadata and `CONSTANT_InterfaceMethodref` with known **interface** metadata. If owner class/interface metadata is unavailable, the checker leaves it unresolved rather than inferring a broken link.
- `tools/r457/audit_jvm_callsite_constraints.py` compares these findings with inherited R456 actual instruction sites and resolved member staticness counts. `invokedynamic` remains separately counted and **unresolved**, not assigned an imaginary owner.

These constraints are **static syntax and reconstruction triage evidence only**. They do not prove that any instruction is reachable or executed, that the JVM resolves the selected owner, that an object has been correctly initialized by a constructor, that stack types match, or that a potential syntax defect actually occurs in the original client.

## Safety and owner-only workflow

R457 inherits R456→R455→R454→R453→R452→R451→R450→R449→R448→R447→R446 input admission. Its owner-side CLI requires the exact SHA-pinned v309 original JAR `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38` with **10,502 classes and 419 resources**, the isolated R421 tree with **1,277 Java sources and 1,394 compiled Java 11 classfiles**, SHA-pinned Store source/class and the R239/R218 dependency inputs. R457 independently reopens all rebuilt classfiles with per-file SHA checks, rereads both dependency JARs under ZIP/SHA limits, validates selected declarations, compares opcode counts against R456, and reobserves the *entire current owner inventory* afterward.

Default execution produces **aggregate counts only** and no private owner paths, source names, class identities, resources, method names, bytecode or JAR hashes in stdout:

```powershell
python -B tools\r457\audit_jvm_callsite_constraints.py --original-v309-jar '<owner-local exact pinned v309 client.jar>'
```

To opt into a detailed *private-only* name/descriptor/PC worklist, append `--save-private-unapproved-worklist`. The full audit then runs twice and checks the complete current R421 source/class/dependency SHA inventory, full details and summary identity before writing exactly one new **exclusive owner OS TEMP** folder named `SpawnPK-R457-Private-Callsites-...` containing `R457-UNAPPROVED-CALLSITE-CONSTRAINTS.json`. Prior reports are never overwritten; no original source/JAR/class bytes are copied or uploaded publicly. `--resource-companion-root` retains inherited read-only companion-resource byte checking without packaging assets.

These present-day SHA scans **do not substitute for the missing independently approved historical R421 full source/class inventory** required by R442/R440/R425/R432. No historical approval is asserted or created automatically.

## Verification and remaining reconstruction work

**48 new fabricated synthetic tests**, on Windows/Ubuntu × Python 3.11/3.13, cover valid and malformed method descriptors; J/D category-two slot accounting; arrays; exact `invokeinterface` receiver/argument count and excess lengths; constructor `invokespecial`, class-vs-interface CP kind and return requirements; forbidden `<clinit>` calls; missing owner uncertainty; forged synthetic evidence; backward compatibility with R456; multi-issue classification; distinct `invokedynamic`; exact SHA-pinned synthetic owner gates; default read-only, private no-overwrite and mutation-between-scans denial. All inherited R456–R445, R442 and R426 synthetic suites are in the CI matrix. None of these public tests contains real private recovered SpawnPK source or assets.

The owner PC `DESKTOP-LTXXO4K` remains offline. Actual recovered source, historical R421 baseline, v309/v312 live Java runtime, assets, GUI, login, gameplay and compile/launch acceptance remain unverified. The full original client has **not** been reconstructed and proved runnable. Static syntax checks are not a substitute for a real bytecode verifier or real JVM linkage.

**Keep draft/unmerged. No production client replacement, persistent player-history reads/writes, deletion-intent/ack marker cleanup, R415/R417 write-fence bypass or release authorized.**

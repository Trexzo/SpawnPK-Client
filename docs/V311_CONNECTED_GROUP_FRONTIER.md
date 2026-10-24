# Original v311: bounded, dependency-closed source **group** frontier

**2026-10-22.** This extends the already SHA-pinned `original-source-frontier`
tool. It proposes *possible next reconstruction batches* from the original
private JAR. It does not recover any new proprietary Java source, compile a
candidate, establish bytecode parity or authorize full-client publication.

## Why the earlier single-class frontier is incomplete

The existing direct frontier only identifies an unrecovered class when **every**
explicit original `rs/` class dependency is already in the selected group.
That cannot identify a chain `Next -> Helper -> selected Base`, or a mutually
dependent pair `Painter <-> Label`. Even a source-buildable two-class addition
is missed if neither class is independently closed.

The new `dependency_closed_group_candidates` worklist computes the explicit
*transitive* project-class dependency closure for each unrecovered class.
A candidate is listed only when all additional referenced `rs/` classes:

1. exist as classfiles in the exact SHA-pinned original JAR;
2. fit within the bounded group size; and
3. occur in the **same** proposed batch, or in the hash-attested selection.

It deduplicates identical closures (including both roots of a cycle), marks
unanchored but mutually connected JDK-only groups separately, and prioritizes
groups without Java class/package namespace collisions. The original
`candidates` single-class report remains unchanged for existing consumers.

## Local private invocation

```powershell
spk-recovery original-source-frontier `
  C:\private\client-v311.jar `
  --source-authority C:\private\v311-verified-source-selection.json `
  --max-candidates 30 `
  --max-group-size 8 `
  --out C:\private\v311-closed-groups.json
```

The authority JSON must have `original_jar_sha256` and
`original_class_sha256` mapping original `rs/...class` entries to their
verified exact hashes. The tool rejects incorrect JAR/class hashes, missing
selected classes, a selected group with an explicit dependency outside the
selection, duplicate archive entries, invalid limits and an existing report
path. The size cap is 2–32 additional classes, default eight. A group is
**proposed only**: `source_reconstructed=false`,
`compile_or_runtime_parity_proven=false`.

The group report includes sorted class paths and original SHA-256 fingerprints,
additional class count/bytes, internal explicit dependency edge count,
dependencies to the selected source set, and namespace-collision flags.
It never writes source code, classfiles, the original binary or compiled
client artifacts.

## Important interpretation boundaries

A class closure is computed from the existing conservative JVM parser:
constant-pool class/descriptor references, own field/method declarations and
generic signatures. It is **not** a full Java compile dependency oracle.
It does not resolve reflection, annotations not parsed by that scanner,
`ServiceLoader`, dynamically loaded classes, resources, JNI, runtime assets
or the Java source alias strategy for `rs.t` namespace collisions. A batch
may need changes to alias handling or may fail to compile, and is therefore
never automatically promoted. Every authentic candidate still requires a
private source reconstruction, a no-original-classpath multi-source Java build,
exact instruction/declaration/constant/BootstrapMethods checks where relevant,
and representative isolated behavior comparisons.

The public regression `tests/test_v311_connected_group_frontier.py`
compiles only unrelated synthetic Java9 classes. It tests an anchored
two-class chain, a mutual cycle, an unanchored cycle, and refusal to accept a
class whose required `rs/` dependency is **absent** from the archive. It also
checks limit enforcement, original SHA authority, incomplete base selection and
non-overwrite behavior on Windows/Linux CI.

**Authentic v311 status is unchanged by this tool change:** the last confirmed
private evidence is 47 distinct source-rebuilt classes / 2,223 instruction
matches across separate builds, not one 47-class javac invocation and not a
fully source-buildable game client. The original JAR and recovered Java stay
private. PR #1142 remains draft and unmerged.

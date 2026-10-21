# Original v311 — independently reconstructed named-timer registry `rs/y/d`

**Date:** 2026-10-21. Real private user-uploaded original JAR, SHA-256
`5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`.
No original class bytes, proprietary Java source, original binary, compiled
game classfiles or private runtime harness are committed to the public GitHub
repository.

## New actual original-client source recovery

The next direct original-project dependency-closed candidate after the
previously proved 35-class source island and separately recovered timer
`rs/y/a` is **`rs/y/d.class`** (1,160 bytes), whose only original `rs/`
references are `rs/y/a.class` and `rs/y/b.class`. It implements a
`Map<String, rs.y.b>` keyed timer registry with add, repeat-add refusal,
replace/reset, activity, remaining time, remove, clear and a map accessor.

| Evidence | Observed result |
|---|---|
| Original `rs/y/d.class` SHA-256 | `488ce7b5ba4e1749ba7620c45749772bafaa38231e0d640fb5996712fa445526` |
| Independently compiled `rs/y/d.class` SHA-256 | `f39500d21ce3f42c7884dd0b6c2349d3bbb70b32dab8ff78b309bdca3a8bf2c8` |
| Original source-to-bytecode witness | **81/81 ordered JVM instructions**, exact offsets, branch targets and resolved symbolic operands, complete declarations/descriptors |
| Direct original project dependencies | **2**, both already source-recovered: `rs/y/a` and `rs/y/b` |
| JDK target and compiler classpath | `javac --release 9 -proc:none -g:none`, **empty original-game binary classpath/sourcepath** |
| Original reconstructed dependency classes | `rs/y/a` 35/35 JVM instructions, `rs/y/b` 3/3, and zero-Code interface `rs/y/c` declaration parity |

A **four-source connected Java compilation** of actual privately
reconstructed `rs/y/a`, `rs/y/b`, `rs/y/c` and `rs/y/d` succeeds.
All four source-built class declarations and ordered original JVM
instructions match the exact original v311 classes (119 total executable
instructions in this four-source subset). This is a separately verified
source group, **not** evidence that all 38 distinct source-recovered classes
compile together in one `javac` process.

The `rs/y/a` branch-sensitive source form uses the exact original
`ifne`/remaining-time control flow; its rebuilt class SHA-256 remains
`fa55105116e3a2f61aaa25466d6ca3934ea45e1fcb923d718fb99235a35320b1`,
matching the earlier
[original timer recovery](V311_TIMER_BRANCH_PARITY_RECOVERED.md).

## Original versus reconstructed JDK-only behavior

A separately compiled test harness was executed with the **original JAR**
and then with only the independently rebuilt Java9 classes in the
application classpath. It exercised an initially empty registry,
adding a long-lived entry, duplicate-add refusal, active and
positive remaining-time queries, replacement/reset, removal,
missing-key remaining-time fallback, an already expired entry,
re-adding an expired entry, and clearing the registry.

Both classpaths returned exactly:

```text
true|true|false|true|true|1|true|false|0|true|false|true|true
```

The original-JAR behavior probe also repeated with the same output. Large
positive and negative durations were chosen to minimize wall-clock
boundary ambiguity; elapsed times were **not** compared numerically.
This is a bounded JDK-only behavioral comparison, not game runtime,
server behavior, multithreading, exhaustive timing verification or
graphics acceptance.

## Aggregate progress, with precise scope

Previously, **35 original v311 Java classes were compiled together** in
one separate source island with **1,059/1,059** matching original JVM
instructions. Separately, `rs/y/a` (35/35) and the UI text renderer
`rs/ui/components/x` (198/198) had been source-rebuilt and verified.
Adding `rs/y/d` (81/81) means:

- **38 distinct independently source-recompiled original `rs/` classes**
  across the combined prior records and this recovery;
- **1,373 original executable JVM instructions** matched across the
  corresponding independent proof records;
- **35** remain the maximum class count supported by an actual
  **single combined original-v311 Java compilation**, not 38.

No full 1,184-class v311 source build, complete classfile
attribute/StackMapTable byte identity, full dynamic dependency closure or
original v309-to-v311 semantic class/member lineage is claimed.

## Repeatable public regression

`tests/test_v311_timer_registry_source_island.py` builds an **unrelated
synthetic Java9** three-class chain: abstract clock, concrete clock
subclass and `Map<String,BaseClock>` registry. It verifies that original
exact-SHA-attested dependency-frontier discovery first offers the
concrete subclass and **only after adding its class SHA to the selected
manifest** offers the registry. It then checks a true independent
three-source `javac` rebuild with complete JVM symbolic-instruction
parity, and fails closed on omitted selected dependencies and wrong
original class SHA before creating output.

The hosted regression uses synthetic, JDK-only source. **It cannot
reproduce the original `rs/y/d` comparison on GitHub**, because
the actual client and reconstructed private Java are not checked in.

Next original-source target selection should use the newly attested
timer registry as a verified dependency; scene and client integration
still require many additional dependency and original-identity proofs.

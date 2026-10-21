# v311 original-client project-class surface (2026-10-21)

This is **real read-only evidence from the original uploaded v311 client JAR**, not a decompile, source release, byte-identical rebuild, or game launch. No JAR, cache, Java source, embedded literals, server addresses, or credentials are committed.

## Exact original authority

- Private input: `client(20261021-111920).jar`
- SHA-256: `5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268`
- ZIP entries: **10,947**, of which **10,527** are JVM class entries and **1,184** are under `rs/`; no duplicate ZIP member names, direct traversal entries or CRC errors were seen.
- All **1,184** original `rs/*.class` members have classfile major version **53** (Java 9 bytecode). This is a bytecode target, **not** a claim that building the recovered source needs no later JDK.
- Sum of uncompressed project-class entries: **3,709,911 bytes**.
- SHA-256 of the canonical sorted `rs/` project-class path/digest rows: `c9a88342e8f1d3eed57d113d0691b8ffb0014c46947637437705e03159e4d535`.

Each digest row is UTF-8 bytes `class-entry-path + NUL + lowercase SHA256(uncompressed class entry) + LF`; rows are sorted by complete ZIP member path. This fingerprint uniquely attests to the observed **content + location** of the project-class entries. It is not a cross-version class identity or semantic-name witness. `src/spk_recovery/indexer.py:project_class_surface` reproduces this from a fully parsed recovery index and explicitly rejects unparsed classes or inconsistent internal names.

## Actual observed distribution

| ZIP package prefix under `rs/` | Class entries |
|---|---:|
| `n/` | 173 |
| `l/` | 171 |
| `plugins/` | 155 |
| `gui/` | 106 |
| `ui/` | 91 |
| `o/` | 53 |
| Classes directly under `rs/` | 51 |
| `runelite/` | 44 |
| `r/` | 37 |
| `d/` | 36 |
| `k/` | 35 |
| `cache/` | 29 |

These are **obfuscated package labels**, not a source-workload estimate or proof of functional ownership.

## Critical source-recovery boundaries

- `rs/f/a.class` exists, class SHA-256 `01f0546471ba05b71cf4ceb8245f76fde9c3306375db41ef21323c8885d0281e`; original `ConstantValue` build 311 was independently inspected previously.
- `rs/Client.class` exists, SHA-256 `f37d249f40eb212086d334777dc5e9e707276a7cf129f6a00955071b5d9bda98`, uncompressed length **290,805** bytes.
- `rs/gui/Launcher.class` exists, SHA-256 `6b8eaea0b78fbb60e1d6e92497f6a5f8ab25a297e72d49889980fd224c1d9d27`.
- `rs/cache/osrs/util/OsrsMapDependencyScanner.class` exists, SHA-256 `fee0729269f73923a073cbfd658ac26c66b0d7db46446992e3428451385d317a`.
- `rs/eventbus/EventBus.class` exists, SHA-256 `7bcd16369a679f743b644bdf62c4b39dc50608ccbdbfe4768d142a7fc7af8259`.
- **`rs/Scene.class` and `rs/s/e/c.class` do not occur under those names in this v311 ZIP.** This does *not* prove scene logic was removed. They might have been renamed, repackaged, replaced or otherwise absent. Only cross-build class/method evidence can establish relationships.


## Recovered original v311 scene-role topology (structural candidate, not source transfer)

A further **actual original-v311 classfile inspection** located a uniquely shaped
scene-grid holder in `rs/V.class`, with original SHA-256
`c9d927a22fd77905b93c455f7135c83408b534cd71cc767ca962827f9b144a0c`.
Its structure matches the **role** of a 4-plane scene:

- 77 fields, 66 methods, and a `([[[I)V` constructor taking terrain height arrays;
- an instance tile array `rs/H[][][]`, and a static `boolean[][][][]` visibility grid;
- the constructor sets **4 planes and 104×104 tiles** and allocates the 3-dimensional `rs/H` grid accordingly;
- the original `rs/Client.class` holds a field of descriptor `Lrs/V;`;
- the tile type `rs/H.class` (SHA-256
  `ae42657b2cf14f40ce4966d77a714734d4b9ac73560dfd1753fed213f78c6d7a`)
  has 24 fields, 12 methods, a `(III)V` position constructor, a `Lrs/H;`
  self-link and an array of scene-entity references.

These are direct classfile structure and constructor-instruction observations,
**not inferred solely from one name/size**. `src/spk_recovery/scene_role_candidates.py`
checks six independent topology witnesses on a fully parsed private original
index, after verifying the exact v311 original JAR SHA and the complete project
class path/content fingerprint. Ambiguous/missing candidates cause refusal.

Run the read-only candidate probe after the existing `spk-recovery index`
command on a locally owned original JAR (no extra R308 archive is needed):

```powershell
spk-recovery index C:\private\client-v311.jar --expect-sha256 5b619b82a8ed976d2051f84cda98815943d1ddb82afac9d49f3126f829101268 --out C:\private\v311-index.json
spk-recovery scene-role-candidates C:\private\v311-index.json --expected-new-authority .\authority\v311.json --out C:\private\v311-scene-role.json
```

The command never writes into the JAR or original index, refuses overwriting
an existing result, and reports **only** class-path role candidates and
structural summary. No source, private bytecode, cache, asset or proprietary
constants are published. A scene-role witness is **not proof** that `rs/V`
is byte-identical/semantically the same as historical R308 `rs/Scene`; that
must be established from an authenticated earlier original-client index/JAR
using class/method evidence. Historical R308 fixes must **not** be applied
automatically to original v311.


## Actual original-v311 Scene member worklist (not a bug report)

A separate SHA-gated **read-only** `javap -c -p -s rs.V` scan of the
exact original v311 JAR identified **66 total scene methods**, including its
static initializer. **42** directly reference the `rs/V.i:[[[Lrs/H;`
tile-grid field. **22** of those also contain a general array-store
(`aastore`) or an `rs/H` tile-object field write (`putfield`).

These 22 are **mutation-review candidates, not 22 confirmed writes to the
scene tile grid and certainly not 22 bugs**. The `aastore` instruction may
target an unrelated array; the scan does not perform stack/alias analysis.
Presence or absence of a conditional branch before the *first* grid field
read does not prove bounds safety, because caller invariants and later
guards also matter.

Examples worth classifying during recovered-source reconstruction include
the direct four-integer scene operation `(IIII)V`, two-integer scene update
`(II)V`, the `(IIIB)V` tile-object operation, and the
`i/k/l(III)V` methods. Their existing obfuscated names/descriptors are
identifiers **within original v311 only**. In particular, they are not
automatically assigned historical R308 method names.

New `src/spk_recovery/scene_member_frontier.py` reproduces this review
worklist from the original JAR on the owner's machine, after checking the
exact JAR and `rs/V.class` SHA-256. It invokes local `javap` without a
shell, refuses malformed/partial disassemblies or changed observed census,
and emits per-method signatures, opcode-sequence hashes, and aggregate
grid/read/store/conditional counts. It does **not** embed a proprietary
bytecode instruction transcript in the report.

```powershell
spk-recovery scene-member-frontier C:\private\client-v311.jar --expected-new-authority .\authority\v311.json --out C:\private\v311-scene-method-frontier.json
```

This gives a focused method-level cross-version research queue. A real
**original v309 or v310** bytecode/index is still needed to prove
individual class/member correspondence. No v311 source build, bounds-fix
port, graphical run, or verified vulnerability is claimed here.

## How this moves recovery forward

1. **Keep** v308 rebuilt Java regression evidence and the original v309 authority on their original versions. v311 is a distinct original-client release.
2. **Obtain an independently SHA-verified complete v309 or v310 original index/JAR**, and run the existing `spk-recovery update-intake` / `update-migrate` pipeline to v311. v309’s earlier original SHA authority is `ff5a58d9dc2bf7b75d7346aa6b711ebd423435e04c3f4e1f0d1de874c6d08f38`; use that only for the actual original version, not the R308 privately rebuilt class-only JAR.
3. Transfer Java source/class semantic identities **only for exact/uniquely structurally proved matches**. Queue ambiguous, modified and unmatched classes. Focus initial human review on the scene/viewport family, `Client` and changed GUI/cache paths **after** matcher results confirm identity.
4. Only then produce a complete independent `recovered-source/v311/src/**/*.java` snapshot and apply the existing zero-fallback clean Java source build/provenance gates. No historical Windows Cooking ZIPs are prerequisites to these source-recovery tasks.

**Unresolved as of this observation:** no actual verified v309/v310-to-v311 class delta, no proof of class identity for absent old paths, no v311 complete source rebuild, and no native owner gameplay test. Do not infer any of these from the project-class fingerprint.

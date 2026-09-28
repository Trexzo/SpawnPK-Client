# Chat 2 handoff to R3M/R3N canonical field proof

Chat 2's client(5) -> exact-v308 field research discovered that surviving ProGuard field
spellings are not always stable logical identities.

The strongest concrete example is:

```text
rs/n/c/aD
old bG:I -> new bI:I
old bH:I -> new bJ:I
old bI:I -> new bK:I
```

Matched-method bytecode positions and initializer behavior both support that shift, so a
same-symbol `bI -> bI` transfer is not trustworthy.

## What moved to core

Main now owns the canonical implementation of the stronger trust boundary:

- **R3I** rejects weak field transfer authority;
- **R3L** requires JAR-bound proof for exact-position transfer;
- **R3M** recomputes field position proof from exact old/new JARs plus canonical class and
  method lineage;
- **R3N** integrates that JAR-bound proof into `update-migrate`.

R3M's signature is aligned with the Chat 2 finding:

- canonical method ID;
- GET/PUT operation;
- own-field access ordinal;
- exact bytecode offset;
- normalized descriptor identity;
- unique on both builds;
- at least two observations.

That is now the canonical path for changed-class field transfer.

## What remains in Chat 2

PR #9 intentionally no longer carries a second bytecode profiler/proof/reconciliation
engine.

Chat 2 retains only the distinct intelligence layer:

- baseline cross-build member research;
- advanced exploratory field evidence (usage, neighborhoods, alignment, ConstantValue);
- the real-corpus stable-symbol contradiction artifacts;
- semantic candidate/confidence/provenance tooling;
- semantic dossier ranking;
- exact-v308 semantic candidates and R2C2 review artifacts.

The field conflict/reconciliation JSON documents remain as research evidence from the
client(5) -> v308 audit. They are **not** canonical member lineage and must not bypass
R3M/R3N JAR-bound proof.

## Current interpretation

The historical `5,450 / 5,482 = 99.42%` number is gross research relationship coverage,
not a precision claim.

Canonical field authority for future builds should be measured after R3M/R3N proof and the
R3 authority finalization gates, not by Chat 2's pre-proof matcher count.

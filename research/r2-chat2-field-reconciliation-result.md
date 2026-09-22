# Chat 2 — exact-position field reconciliation result

Date: 2026-09-22

This pass reconciles the 13-class field-identity hard tail using the same descriptor
identity model as the repository matcher plus exact matched-method field-access positions.

## Exact corpus

- alternate client: `client(5).jar`
- alternate SHA-256: `a9a5d1f35a6657b5c26939ca30e008748e718f6b206cc8fd93b64b57c4833385`
- exact v308: `client(6).jar`
- v308 SHA-256: `854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

Minimum exact-position evidence: **2 matched observations**.

## Reproduced pre-reconciliation tail

The exact classfile replay reproduces the repository's previous hard tail exactly:

```text
classes                 13
fields                 305
gross relationships    273
gross unresolved        32
gross tail coverage  89.51%
```

The per-class unresolved counts match the earlier validation report exactly.

## Reconciliation

Exact-position precedence does two things:

1. removes an existing relationship when a unique exact-position identity claims either
   endpoint differently;
2. overlays the exact-position relationship only when it remains one-to-one.

Result:

```text
contradicted relationships dropped   30
exact-position relationships added   44
reconciled relationships            287 / 305
remaining unresolved                 18
reconciled tail coverage          94.10%
```

This is a **net gain of 14 verified relationships** while also removing bad same-symbol
and structural edges.

Applied to the historical 5,450/5,482 research graph, the same net change would yield:

```text
5,464 / 5,482 = 99.67%
```

That **99.67% is not canonical R3 authority coverage**. R3I deliberately applies a
stricter transfer rule: a changed-class field is automatically transferable only when it
has exact matched-method access-position evidence (or lives in a byte-identical class with
a safe stable-symbol relation). Other changed-class fields remain review blockers.

The useful certified statement from this pass is therefore:

> the previously ambiguous 13-class tail is reduced from 32 to 18 unresolved fields by
> exact-position reconciliation without residual-position guessing.

## Remaining 18

The remaining fields are concentrated in seven classes:

| Class | Remaining |
| --- | ---: |
| `rs/n/c/G` | 1 |
| `rs/n/c/c/a` | 4 |
| `rs/n/c/c` | 3 |
| `rs/n/c/O` | 3 |
| `rs/n/c/aw` | 2 |
| `rs/n/c/h` | 1 |
| `rs/n/c/d/a` | 4 |

Machine-readable coordinates are stored in:

`mappings/candidates/client5-to-v308.fields.reconciled-summary.chat2.r2.json`

These 18 should move only with stronger evidence such as widget/config joins,
constructor-source identity, packet flow, resource/string associations or direct semantic
consumer evidence.

## R3 integration

R3I-R3K now provide the correct core boundary:

- weak changed-class field identities are review-only;
- `exact_matched_method_access_positions` is trusted field evidence;
- unresolved field review blocks authority finalization.

Chat 2's audited workspace now additionally emits a reconciled candidate set and runs R3G
member-delta classification on that reconciled view, so contradicted same-symbol fields
cannot be reported as `member_shape_unchanged`.

# R2 Chat 2 — advanced field identity validation

Date: 2026-09-22

This pass continues the field-identity tail from the earlier matched-method GET/PUT
analysis. It remains research-only and does not mutate canonical member lineage.

## Exact corpus

Alternate lineage:

- `client(5).jar`
- SHA-256 `a9a5d1f35a6657b5c26939ca30e008748e718f6b206cc8fd93b64b57c4833385`

Exact v308:

- `client(6).jar`
- SHA-256 `854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

Only the 1,046 strongest R1 class pairs are used here: 513 exact-entry identities plus
533 unique name-insensitive structural identities.

## Result

The declaration/type-lineage matcher started at:

```text
fields                 5,482
declaration matched    5,404
unresolved                78
```

Six conservative post-declaration stages now recover 46 of that tail:

| Stage | Added |
| --- | ---: |
| matched-method local GET/PUT signature | 11 |
| cross-owner matched-method GET/PUT signature | 2 |
| exact matched-method instruction neighborhood | 9 |
| exact constructor/static-initializer instruction neighborhood | 13 |
| mutually dominant normalized instruction alignment | 8 |
| exact JVM ConstantValue identity | 3 |
| **Total post-declaration** | **46** |

Final current field identity:

```text
matched       5,450 / 5,482
coverage      99.42%
unresolved       32
```

Candidate artifact:

`mappings/candidates/client5-to-v308.fields.advanced.chat2.r2.json`

## New evidence stages

### Cross-owner usage

The first usage pass looked only at reads/writes made by methods in the field's own owner.
The new pass also uses already-matched methods in other authoritative class pairs. A field
is transferred only when the complete caller-method + GET/PUT signature is unique on both
builds.

This adds two exact-context relationships:

- `rs/n/c/c.bH:I -> bJ:I`
- `rs/n/c/O.bQ:J -> bS:J`

### Exact instruction neighborhoods

For unresolved GET/PUT instructions, surrounding bytecode is normalized using already
proven class, method and field identities plus exact constants. The target field name is
removed from the fingerprint.

A field is transferred only when the complete neighborhood fingerprint is unique on both
builds.

Matched-method neighborhoods add 9 fields. Adding conservatively matched constructors and
static initializers as evidence-only anchors adds another 13.

Constructors remain excluded from semantic method identity; they are used here only as
field-initialization evidence.

### Full normalized instruction alignment

For the still-unresolved tail, already-correlated method/initializer instruction streams
are normalized and aligned. Aligned unresolved field accesses vote for a correspondence.

A relationship is accepted only when:

- aligned vote count is at least 2;
- it is the strongest outgoing edge for the old field;
- it is the strongest incoming edge for the new field;
- outbound dominance is at least 0.80;
- inbound dominance is at least 0.80.

Eight relationships survive that gate. Six have 100% two-way dominance. The two
`rs/t/a` string fields survive at 5/6 (0.833333) and 4/5 (0.80) respectively.

### ConstantValue

The JVM `ConstantValue` payload is stronger than field declaration order. Three
previously unused static-final fields have unique exact constants across the two builds:

- `rs/n/c/ac.bS:I (32) -> bU:I (32)`
- `rs/n/c/ac.bT:I (20) -> bV:I (20)`
- `rs/n/c/aw.bG:I (60205) -> bI:I (60205)`

Changed constants are not used as fuzzy evidence.

## Remaining 32

The unresolved tail is now limited to 13 class pairs:

| Class | Remaining |
| --- | ---: |
| `rs/n/c/ac` | 2 |
| `rs/n/c/G` | 2 |
| `rs/n/c/c/a` | 4 |
| `rs/n/c/ba` | 2 |
| `rs/n/c/aD` | 1 |
| `rs/n/c/c` | 3 |
| `rs/n/c/ab` | 2 |
| `rs/n/c/O` | 3 |
| `rs/n/c/aw` | 3 |
| `rs/n/c/ap` | 2 |
| `rs/n/c/h` | 1 |
| `rs/n/c/d/a` | 6 |
| `rs/n/a/a/a` | 1 |

Some of these have only one residual same-shape field on each side, but they are still left
unresolved when usage/initializer behavior changed materially. Residual one-to-one shape
alone is not treated as proof because a removed field and a newly introduced field can have
the same JVM type/access shape.

Likewise, approximate neighborhood similarity was investigated but is not promoted by this
pass. The new relationships above all come from exact normalized context, bidirectionally
dominant instruction alignment, or exact constant identity.

## Safety boundary

No declaration-order, alphabetical, nearest-obfuscated-name, or residual-position fallback
is used.

The 32 remaining fields should move only with stronger semantic evidence such as:

- exact widget/config joins;
- resource/string association;
- packet flow;
- constructor source-object identity;
- external renderer/controller joins;
- independently recovered domain semantics.

The goal remains precision first: 99.42% with a real unresolved tail is preferable to a
nominal 100% built on unprovable guesses.

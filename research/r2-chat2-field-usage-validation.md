# R2 Chat 2 — matched-method field usage validation

This is a second-stage field identity pass over the remaining field tail after the
lineage-aware declaration matcher.

Exact corpus:

- alternate lineage: `client(5).jar`
- exact v308: `client(6).jar`
- authoritative R1 class pairs: 1,046
- fields already matched by declaration/type lineage: 5,404 / 5,482
- unresolved before this pass: 78 fields across 22 class pairs

## Method

The field-context pass does not use field declaration order.

For each authoritative class pair it:

1. takes the already-proven method relationships as stable anchors;
2. profiles `getfield`, `putfield`, `getstatic` and `putstatic` observations;
3. records each unresolved field's access counts keyed by matched method relationship;
4. includes lineage-aware field descriptor shape and field access flags;
5. transfers a field only when the complete usage signature is unique on both sides.

## Exact corpus result

Additional fields recovered: **11**

Combined field identity:

`5,415 / 5,482 = 98.78%`

Remaining deliberately unresolved:

`67`

The 11 access-context relationships are:

| Class | Alternate field | v308 field |
| --- | --- | --- |
| `rs/n/c/ac` | `bP` | `bR` |
| `rs/n/c/ac` | `bR` | `bT` |
| `rs/n/c/aD` | `bH` | `bJ` |
| `rs/n/c/ab` | `bR` | `bT` |
| `rs/n/c/ab` | `bK` | `bM` |
| `rs/n/c/aq` | `bG` | `bI` |
| `rs/n/c/aq` | `bH` | `bJ` |
| `rs/n/c/aM` | `bH` | `bJ` |
| `rs/n/c/aM` | `bG` | `bI` |
| `rs/n/c/aw` | `bI` | `bL` |
| `rs/n/a/a/a` | `bH` | `bJ` |

These are identity relationships only. They do not imply semantic English names.

## Safety boundary

A same-type field that has the same access pattern as another same-type field remains
ambiguous. The matcher keeps those cases unresolved rather than falling back to source
order, alphabetical order or nearest-name heuristics.

The remaining 67 fields require stronger evidence such as:

- cross-owner read/write relationships;
- constructor assignment sources;
- constant/string associations;
- renderer/widget joins;
- semantic call graph evidence.

Those later signals can improve identity and naming without weakening the conservative
baseline.

# R1 Chat 2 — client(5) -> exact v308 validation

This report is **research output**, not canonical mapping state. The integration/main chat owns persistent logical IDs and schema promotion.

## Inputs

- Alternate lineage: `client(5).jar`
  - SHA-256: `a9a5d1f35a6657b5c26939ca30e008748e718f6b206cc8fd93b64b57c4833385`
  - 10,939 archive entries
  - 10,437 classes
  - 1,099 `rs/**` classes
  - 0 class parse errors
- Exact v308 authority: `client(6).jar`
  - SHA-256: `854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`
  - 10,970 archive entries
  - 10,472 classes
  - 1,129 `rs/**` classes
  - 0 class parse errors

No client binaries are committed.

## R0 baseline reproduced

The existing conservative structural matcher baseline was reproduced exactly:

- **251 unique structural class moves**
- **12 ambiguous structural groups**

## Chat 2 matcher result

With the R1 Chat 2 identity engine on the `rs/**` scope:

- old classes: 1,099
- new classes: 1,129
- matched relationships: **1,074**
- unique exact-entry SHA matches: 513
- unique structural-fingerprint matches: 533
- package-anchor matches: **23**
- residual weighted mutual-best matches: 5
- weighted ambiguous: 10
- unmatched old: 25
- unmatched new: 55

The 23 package-anchor relationships are all renamed/moved relationships beyond the R0 structural-move set, so moved-class recovery rises from **251 to 274** (+23, about 9.2%) before any semantic-name model is involved.

## Package-anchor rule

The package prior is not guessed from obfuscated names. It is derived only from already-proven unique structural moves.

Default gates:

- minimum structural-anchor support: **5**
- minimum source-package dominance: **0.90**
- exact suffix-preserving candidate path after the inferred package migration
- compatible class header/member-count shape
- independent weighted evidence score >= **0.82**
- independent evidence weight >= **0.38**

Observed strong package migrations in this corpus:

| Alternate lineage | v308 | Structural support | Dominance |
| --- | --- | ---: | ---: |
| `rs/d` | `rs/cache` | 20 | 1.00 |
| `rs/e` | `rs/d` | 24 | 1.00 |
| `rs/f` | `rs/e` | 16 | 1.00 |
| `rs/g` | `rs/f` | 8 | 1.00 |
| `rs/h` | `rs/g` | 7 | 1.00 |
| `rs/k` | `rs/j` | 9 | 1.00 |
| `rs/l` | `rs/k` | 31 | 1.00 |
| `rs/m` | `rs/l` | 133 | 1.00 |

Smaller package shifts below the support floor remain unresolved by this stage.

## Precision stance

Package anchors are emitted as **candidate identity relationships**, not canonical logical IDs. The matcher deliberately keeps weak/tied cases unresolved. The integration chat should promote only after checking the latest repo state and manually sampling candidate precision.

The candidate list for this exact run is stored in:

`mappings/candidates/client5-to-v308.r1.chat2.json`

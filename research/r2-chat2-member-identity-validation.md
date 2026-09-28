# R2 Chat 2 — member identity validation

This is Chat 2 research output for Issue #7. It does not mutate canonical remap state.

## Corpus

Alternate lineage:

- artifact: `client(5).jar`
- SHA-256: `a9a5d1f35a6657b5c26939ca30e008748e718f6b206cc8fd93b64b57c4833385`
- `rs/**` classes: 1,099
- parse errors: 0

Exact v308 authority:

- artifact: `client(6).jar`
- SHA-256: `854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`
- `rs/**` classes: 1,129
- parse errors: 0

For member validation, only the strongest R1 class identities were used:

- exact class-entry SHA identities: **513**
- unique name-insensitive structural identities: **533**
- total authoritative class pairs: **1,046**

Package-anchor research candidates were intentionally excluded.

## Member identity algorithm

Within each already-correlated class pair:

1. build a temporary descriptor type map from the already-proven R1 class lineage;
2. preserve exact JDK/external reference types while rewriting known moved `rs/**` types to the same research token on both builds;
3. transfer members whose obfuscated symbol + lineage-aware descriptor + access (+ code length for methods) are unique on both sides;
4. for remaining members, match only a unique name-insensitive structural shape;
5. exclude constructors/static initializers from semantic method identity;
6. leave all remaining collisions/unmatched members unresolved.

No English/semantic names are inferred at this stage.

## Results

| Member kind | Old members | Matched | Coverage | Structural rename recoveries |
| --- | ---: | ---: | ---: | ---: |
| Methods | 5,649 | **5,649** | **100.00%** | **5** |
| Fields | 5,482 | **5,404** | **98.58%** | **42** |

The structural rename recoveries are particularly useful because they prove that member
identity cannot safely be represented as the current ProGuard member name.

Examples of method-name shifts recovered without names:

- `rs/t/a.class a()V -> b()V`
- `rs/t/a.class b()Ljava/lang/String; -> d()Ljava/lang/String;`
- `rs/t/a/e.class d()Lgnu/trove/f/b/cc; -> a()Lgnu/trove/f/b/cc;`
- `rs/t/a/g.class d()V -> a()V`
- `rs/t/c.class d()V -> a()V`

Examples of field-name shifts include:

- `rs/n/c/ac.class bL:I -> bN:I`
- `rs/n/c/ac.class bH:Z -> bJ:Z`
- `rs/n/c/c.class bP:Lrs/m/f/a/k/a; -> bR:Lrs/l/f/a/k/a;`

The descriptor move in the last example is itself consistent with the already observed
class/package migration `rs/m -> rs/l`.

## Interpretation

The result is strong enough to use member identity as the substrate for R2 semantic
naming. In this corpus the authoritative class-lineage descriptor map resolves every
non-constructor method without needing bytecode-similarity guesses:

- semantic names can attach to a member relationship rather than an obfuscated spelling;
- future client builds can transfer accepted names when the member identity survives;
- the remaining field tail becomes the focused target for bytecode read/write and call-graph analysis;
- no direct remap should consume these candidates until the integration/core lane defines
  and verifies its member-promotion boundary.

Next Chat 2 stage: aggregate exact-client research, strings, packet/widget constants and
call/reference context into semantic method/field/class naming candidates with explicit
provenance.

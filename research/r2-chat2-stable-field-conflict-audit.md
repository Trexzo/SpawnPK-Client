# Chat 2 — stable field relationship conflict audit

Date: 2026-09-22

This audit revisits the field-identity result after discovering that a surviving
obfuscated field spelling is not always a surviving logical field identity.

## Exact corpus

- alternate client: client(5).jar
- alternate SHA-256: a9a5d1f35a6657b5c26939ca30e008748e718f6b206cc8fd93b64b57c4833385
- exact v308: client(6).jar
- v308 SHA-256: 854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6

## Finding

The baseline member matcher gives stable-symbol field identity first priority. That is
unsafe when ProGuard inserts or reorders same-shape fields while reusing an old spelling.

The concrete trigger is rs/n/c/aD:

- old bG:I is read at the exact positions occupied by new bI:I;
- old bH:I is read at the exact positions occupied by new bJ:I;
- old bI:I is read/written at the exact positions occupied by new bK:I.

The class initializer independently agrees:

- old bG = 317 -> new bI = 317;
- old bH = 45602 -> new bJ = 45602;
- old bI = 45602 -> new bK = 45602.

Therefore a baseline stable-symbol relation bI -> bI is contradicted by exact bytecode
behavior.

## Conservative audit rule

A contradiction is reported only when:

1. the source field and current same-symbol target have the exact same descriptor/access
   shape, so descriptor aliasing is not involved;
2. the source field has a unique matched-method access-position signature;
3. a different target field has that same unique signature;
4. at least two exact observations support the signature.

The signature includes:

- matched method relationship;
- GET/PUT operation;
- own-field access ordinal inside the method;
- exact bytecode offset.

## Result

Across the 13 classes in the previous unresolved tail:

- definite stable-symbol contradictions (>=2 observations): **23**
- additional one-observation leads retained as non-authoritative: **5**

Machine-readable audit:

mappings/candidates/client5-to-v308.field-stable-conflicts.chat2.r2.json

Affected high-confidence classes include:

- rs/n/c/ac
- rs/n/c/G
- rs/n/c/ba
- rs/n/c/aD
- rs/n/c/ab
- rs/n/c/aw
- rs/n/c/h
- rs/n/c/d/a
- rs/n/a/a/a

## Consequence for the earlier 99.42% number

The previous 5,450 / 5,482 figure is a **gross relationship coverage** figure. It must not
be presented as precision-certified field identity until stable-symbol contradictions are
reconciled.

This audit does not automatically rewrite those relationships. The safe next stage is to
remove conflicting stable-symbol edges as authority, insert only mutually unique exact
position/context edges, and then recompute the unresolved set and coverage.

The objective remains precision first. A lower verified percentage is preferable to a
higher figure containing silently incorrect stable-symbol relationships.

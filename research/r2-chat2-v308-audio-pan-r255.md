# Chat 2 — exact-v308 AudioPan R255

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic result

- `rs/v/a$a` -> `CLIENT_CLASS_001107` -> `AudioPan`
- confidence: **0.999**
- review: `SEMREVIEW_D8FB37267F2D64EE5859`
- unresolved: **0**
- field/method proposals: **0**

## Exact behavior

The nested enum preserves the literals:

- `LEFT`
- `RIGHT`
- `NORMAL`

R66 `Signlink` obtains Java Sound `FloatControl.Type.PAN` and then compares this exact enum:

- `RIGHT` -> `setValue(1.0f)`
- `LEFT` -> `setValue(-1.0f)`
- `NORMAL` -> no directional override

No unrelated exact-v308 consumer survives.

## Naming boundary

`AudioPan` is a descriptive recovery name. It does not assert a verbatim original nested-class identifier.

## Acceptance boundary

R255 remains class-only and non-canonical. Chat 2 performs no semantic acceptance.

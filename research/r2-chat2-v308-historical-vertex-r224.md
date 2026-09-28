# Chat 2 — exact-v308 historical RuneLite Vertex source recovery R224

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R224 recovers one source name that no longer exists in current RuneLite source.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_833F07E8D4884EF03C77`
- field/method proposals: **0**

## Stable ID

- `rs/runelite/a/o` -> `CLIENT_CLASS_000831` -> `Vertex`

## Historical source provenance

RuneLite commit `9e696ac3f2e6099460df51bee4079e636c0830a1` removed the old API
`Triangle` and `Vertex` classes. Its parent `f16cd53d0920f88d6edeb08c2b9c7f005e910f15` still contains
`net.runelite.api.model.Vertex`.

That source class has exactly:

- three final integer coordinates `x`, `y`, `z`;
- a three-integer value constructor/getters;
- `rotate(int orientation)`.

The exact v308 `rs/runelite/a/o` preserves the same state and rotation:

1. `orientation = (orientation + 1024) % 2048`;
2. return the same instance when orientation is zero;
3. read the 2048-entry sine/cosine tables;
4. produce `(x*cos + z*sin) >> 16`, unchanged `y`, and
   `(z*cos - x*sin) >> 16`.

This is a historical upstream source-name recovery, not a descriptive guess.

## Acceptance boundary

Chat 2 does not promote R224. Main/Core may accept it only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_833F07E8D4884EF03C77`.

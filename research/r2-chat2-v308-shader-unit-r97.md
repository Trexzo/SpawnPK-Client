# Chat 2 — exact-v308 Shader.Unit R97

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R97 is a separate non-canonical class-only review for the nested unit record owned by R89
`Shader`.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_74335A2459C0E4FF7A83`
- field/method proposals: **0**

## Stable ID

- `rs/k/m$a` -> `CLIENT_CLASS_000343` -> `Unit`

## Exact structure

The nested exact-v308 class contains only:

- final integer shader type;
- final String resource filename.

Its constructor stores those two values, and its accessors return them unchanged.

R89 `Shader` owns a list of these records. During compilation it uses:

- the integer as the OpenGL shader type passed to shader creation;
- the String as the resource filename resolved through R89 `Template`.

## Historical-name corroboration

Public RuneLite-derived GPU source preserves the enclosing class `Shader` and an exact
nested class:

`Shader.Unit`

with:

- `final int type`;
- `final String filename`;
- the same constructor shape;
- the same compile-loop role.

Because the enclosing owner `rs/k/m` is independently R89 `Shader`, this is stronger
than a generic two-field-record guess.

## Name-collision boundary

Chat 2's committed semantic reviews before R97 contain no other proposal named `Unit`.
The simple name is retained because it is the surviving upstream nested source identifier
rather than expanded into a descriptive but non-source name such as `ShaderUnit`.

## Acceptance boundary

Chat 2 does not promote R97. Main/Core may accept the proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_74335A2459C0E4FF7A83`.

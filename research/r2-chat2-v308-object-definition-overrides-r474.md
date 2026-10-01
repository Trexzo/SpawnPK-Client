# Chat 2 — exact-v308 ObjectDefinition overrides R474

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/c/a/a` -> `CLIENT_CLASS_000080` -> `ObjectDefinitionOverrides`
- proposal: `SEMPROP_5DCB7FEE7207D0A501A3`
- review: `SEMREVIEW_68C17CC21268E1F7F662`

## Exact integration point

The live `rs/d/r` ObjectDefinition resolution path invokes:

`rs/c/a/a.a(definition, objectId)`

after definition decode/post-processing and before the resulting definition is exposed to
scene/menu consumers.

R75 already established the paired `rs/d/r$a` identity as `ObjectDefinitionMode`,
providing an independent domain anchor for the target class.

## Exact override behavior

`rs/c/a/a` owns no fields and no instance state.

Its public entry method:

1. invokes the second static override method;
2. applies an additional small object-id switch.

The second method is a large hard-coded switch covering roughly **680 object IDs**.

Cases mutate the supplied ObjectDefinition directly. Exact mutations include interaction
action arrays and other object-definition presentation/runtime fields. Several ids also
replace actions with explicit widget/menu target id sets.

This is therefore a static post-decode ObjectDefinition override table, not a definition
loader or cache.

## Withheld neighbor

`rs/c/b/a` / `CLIENT_CLASS_000081` is intentionally unnamed.

Its only public Client-taking method immediately returns. Static initialization only derives
one path-like String and creates three empty int arrays. No live semantic consumer or
behavioral contract survives in exact v308.

## Boundary

`ObjectDefinitionOverrides` is a descriptive exact-v308 identity. No lost original source
class name is claimed.

R474 remains non-canonical Chat 2 semantic research only.

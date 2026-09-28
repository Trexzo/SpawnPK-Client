# Chat 2 — exact-v308 SPK Editor Kit support R109

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R109 is a separate non-canonical class-only review for two live support types used directly
by R107 `EditorKitController`.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_01DD6A54DB9450818CAB`
- field/method proposals: **0**

## Stable IDs

- `rs/l/b/a/b/a` -> `CLIENT_CLASS_000374` -> `EditorKitNotification`
- `rs/l/b/a/e` -> `CLIENT_CLASS_000379` -> `EditorEntityDistanceComparator`

## EditorKitNotification

EditorKitController owns a list of this type.

Its status-output path:

`c(String)`

prepends a new instance containing the message.

Construction stores:

- the String;
- the current `System.currentTimeMillis()`.

The object remains active for exactly:

`5000 ms`

and the controller removes it after that lifetime.

While active, the notification renders:

`@yel@[!] @whi@<message>`

using the editor/client font. The draw path temporarily changes font alpha according to
elapsed time, producing the exact fading behavior.

The exact incoming-reference index shows no external owner beyond EditorKitController.

## EditorEntityDistanceComparator

The class implements:

`Comparator<EditorEntity>`

and is instantiated by EditorKitController immediately before entity update/render.

For each entity it calculates:

- `dx = entityX - Client.cJ`
- `dy = entityY - Client.cL`
- `ceil(sqrt(dx^2 + dy^2))`

It then returns:

`distance(second).compareTo(distance(first))`

so entities are sorted in descending / far-to-near distance order.

The controller:

1. copies the live EditorEntity list;
2. sorts the copy with this comparator;
3. iterates the resulting list through each entity's shared update/render method.

That fixes both the comparator domain and ordering semantics.

## Deliberate exclusions

R109 does not name `rs/l/b/a/b/b` or its enum.

That helper parses `./debug/textures.txt` sections named `TEXTURES`, `RANDOMIZE` and
`RECOLOR`, but its model-processing method is empty and exact-v308 incoming references are
limited to itself/its enum. It is therefore not promoted merely because its file format is
readable.

## Acceptance boundary

Chat 2 does not promote R109. Main/Core may accept either proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_01DD6A54DB9450818CAB`.

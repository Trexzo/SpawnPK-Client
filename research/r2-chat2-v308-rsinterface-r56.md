# Chat 2 — exact-v308 RSInterface semantics R56

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R56 replaces an initially drafted stream/archive batch that was rejected by the branch's
duplicate guard because R29 already owns Stream, StreamLoader, BZip2Decompressor and
BZip2State. Those duplicate proposals were not retained.

The corrected R56 is a separate non-canonical single-class semantic review for the global
widget/interface definition object.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_42DD35214AC4AE229B6C`
- field/method proposals: **0**

## Stable-ID verification

Core's exact `seed_lineage()` ordering over the complete `rs/` baseline gives:

- `rs/n/e` -> `CLIENT_CLASS_000684`

## `rs/n/e` -> `RSInterface`

The main interface loader receives StreamLoader/font resources, decodes interface data
through Stream, allocates a global `rs/n/e[]` table and constructs each interface record
by numeric id.

The exact state surface contains the expected widget families:

- child ids and child X/Y position arrays;
- dimensions, scroll/layout and parent/id metadata;
- inventory item-id and amount arrays;
- comparison/script arrays;
- Sprite references and sprite arrays;
- font/model references and model animation state;
- text, action, tooltip and spell/use strings;
- option arrays and many interaction/display flags.

The class also contains extensive static helpers that create or mutate custom interface
records directly in the same global table.

Surviving literals include `Ok`, `Select`, `Continue`, `Close`, cast/use text,
equipment resources, prayer sprites and many interface-specific resource names.

That contract fixes the classic semantic identity as `RSInterface`.

## Naming boundary

`RSInterface` is a semantic/historical recovery name grounded in exact v308 behavior.
It remains non-canonical until explicit Main/Core acceptance.

## Acceptance boundary

Chat 2 does not promote R56. Main/Core may accept it only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_42DD35214AC4AE229B6C`.

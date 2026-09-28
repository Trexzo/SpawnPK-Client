# Chat 2 — exact-v308 world-event option markup renderer R294

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic result

- `rs/n/c/b/b` -> `CLIENT_CLASS_000635` -> `WorldEventOptionMarkupRenderer`
- `rs/n/c/b/b$a` -> `CLIENT_CLASS_000636` -> `WorldEventOptionRenderMode`
- review: `SEMREVIEW_2FCD12B3146FCA11C951`
- unresolved: **0**
- member proposals: **0**

## Exact-v308 contract

The already-reviewed Gladiator's Vindication ScriptPacket handler invokes `WorldEventOptionMarkupRenderer` when appending or rewriting dynamic event-option text.

The renderer parses an exact inline markup language including dropdown, NPC, label, sizing, positioning, alignment and line tokens. The resulting widget ids/heights feed the same Gladiator's Vindication interface and its dynamic scroll/layout state.

The mode enum survives with exact constants:

- `STANDARD`
- `DROP_DOWN`
- `ANIMATED_NPC`

The renderer switches behavior from that enum while parsing the corresponding option content.

## Deliberate exclusion

`rs/n/c/b/c` is only the compiler-generated enum switch-map helper and remains unnamed.

## Boundary

R294 is non-canonical semantic research only. No semantic acceptance, source rewrite or source materialization is performed.

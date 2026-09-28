# Chat 2 — exact-v308 Adventure Book task entry R296

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic result

- `rs/n/c/c$b` -> `CLIENT_CLASS_000642` -> `AdventureBookTaskEntry`
- review: `SEMREVIEW_0F75C45E005AD043BD22`
- unresolved: **0**
- member proposals: **0**

## Exact-v308 contract

The record stores:

- retained `AdventureBookTaskTargetType`;
- target id;
- primary and optional secondary task text;
- an int-pair array used by the task's item/reward presentation;
- current progress;
- goal progress;
- completion state.

Its formatter replaces the exact `{prog}` token with the live current/goal pair.

The already-owned `AdventureBookInterface` consumes this record to:

- select ITEM / NPC_HEAD / OBJ target rendering;
- choose incomplete/completed state sprites;
- render one or two task-description lines;
- materialize the record's item-pair array.

## Boundary

R296 is non-canonical semantic research only. No semantic acceptance, source rewrite or source materialization is performed.

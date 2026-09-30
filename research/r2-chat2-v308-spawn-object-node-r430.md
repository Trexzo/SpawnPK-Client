# Chat 2 — exact-v308 SpawnObjectNode R430

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/N` -> `CLIENT_CLASS_000041` -> `SpawnObjectNode`
- proposal: `SEMPROP_37FD54B700B507B53128`
- review: `SEMREVIEW_56D88538BCF98F6D16C2`

## Exact Node/list role

`rs/N` extends the recovered classic `Node` base and is stored in a dedicated Client
Node list.

The constructor initializes one object-id field to **-1**.

## Scene-state capture

Before applying a queued object change, Client resolves the record's:

- plane;
- local x/y tile;
- scene-object category.

It queries the recovered Scene object for the existing object tag/config and stores the
current:

- object id;
- shape/type;
- orientation

back into the record.

## Two-stage countdown lifecycle

The live spawned-object processing loop owns two countdowns.

When a countdown reaches zero, Client validates the relevant object definition and invokes
the scene-object replacement/update routine using the queued coordinates, category, id,
shape and orientation.

The Node removes itself after the corresponding update has completed or become redundant.

## Enqueue/update path

Client searches for an existing queued record matching plane/x/y/category.

If absent it:

1. constructs `rs/N`;
2. stores the scene coordinate/category;
3. captures the existing scene object state;
4. links the record into the queue.

It then updates the requested replacement id/orientation/shape and the two delay/lifetime
values.

## Historical identity

Historical 317 sources preserve the same Node subclass as `SpawnObjectNode`, including the
constructor's `-1` sentinel and the same queued spawn-object loop.

The historical name is corroborative. Exact-v308 behavior remains primary authority.

R430 remains non-canonical Chat 2 research only.

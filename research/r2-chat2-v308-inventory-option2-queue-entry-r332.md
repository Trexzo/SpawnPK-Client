# Chat 2 continuation — inventory option 2 queue entry R332

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/q/a/a`
- stable ID: `CLIENT_CLASS_000744`
- semantic: `InventoryOption2QueueEntry`
- review: `SEMREVIEW_3BDB9F685F12896844CD`

## Exact producer

The exact Client menu branch for menu action **454** normally emits opcode 41.

Under the branch's defer/gating condition it instead constructs:

`new rs/q/a/a(actionInt1, actionInt2, actionInt3)`

and appends the object to `Client.ie`.

The exact-current outbound matrix fixes action 454 as:

- family: inventory item
- C2S: 41
- contract: inventory option 2 / equip alias
- payload: widgetId, slot, itemId

## Exact consumer

A later Client path iterates `Client.ie`.

For every queued entry it writes:

1. opcode 41;
2. `entry.a()`;
3. `entry.b()`;
4. `entry.c()`;

using the same transforms as the direct action-454 path, then clears the queue.

The class itself stores exactly those three integers and exposes only their getters.

## Naming boundary

The class is not itself an `OutgoingPacket`; it is a deferred queue record that later becomes
C2S41.

The name also does not claim `Equip`. Exact-current evidence proves opcode 41 is
context-dependent and can be the ordinary inventory option-2 route or an equip alias.

R332 remains non-canonical semantic research only.

# Chat 2 — deferred inventory action R369

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/q/a/a` -> `CLIENT_CLASS_000744` -> `DeferredInventoryAction`
- proposal: `SEMPROP_7946A1BC633CD23D6C80`
- review: `SEMREVIEW_7ECDDC2C748AB50DBA03`

## Exact lifecycle

The class is an immutable three-int record.

Client constructs it only from exact menu action **454** using the same three values that the
exact-current outbound action matrix identifies for C2S41:

- widgetId
- slot
- itemId

In the normal branch Client writes opcode 41 immediately.

In the deferred branch it appends this record to a dedicated list. A later Client-loop path
waits for the configured interval, iterates the list, writes opcode 41 plus the three stored
values using the same transforms, then clears the queue.

## Naming boundary

C2S41 is explicitly context-sensitive in exact-current authority:

- inventory option 2;
- also used as an option-1 equip alias;
- visible verbs vary by item definition/context.

The class is therefore named `DeferredInventoryAction`, not EquipPacket or
InventoryItemOption2Packet.

## Rejected nearby gaps

- `rs/cache/b/a`: unreferenced one-method interface.
- `rs/i/b$b`: TOP/BOTTOM enum with no live exact-v308 consumer edge.
- `rs/q/b/g`, `rs/w`: empty/no-op classes.
- `rs/x/c+d`, `rs/z/c`: previously withheld dormant state.

R369 remains non-canonical Chat 2 research only.

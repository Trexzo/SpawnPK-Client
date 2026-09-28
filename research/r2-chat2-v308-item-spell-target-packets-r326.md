# Chat 2 — item/spell target outgoing packets R326

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Item-on-target

- opcode 192 / `rs/o/a/a/a/A` / 000713 -> `ItemOnObjectPacket`
- opcode 14 / `rs/o/a/a/a/B` / 000714 -> `ItemOnPlayerPacket`
- opcode 53 / `rs/o/a/a/a/y` / 000711 -> `ItemOnInventoryItemPacket`
- opcode 57 / `rs/o/a/a/a/z` / 000712 -> `ItemOnNpcPacket`

The exact current router table also contains item-on-ground-item opcode 25, but exact v308
has no corresponding generated OutgoingPacket class in this 52-class family.

## Spell-on-target

- opcode 181 / `rs/o/a/a/a/E` / 000717 -> `SpellOnGroundItemPacket`
- opcode 237 / `rs/o/a/a/a/F` / 000718 -> `SpellOnInventoryItemPacket`
- opcode 131 / `rs/o/a/a/a/G` / 000719 -> `SpellOnNpcPacket`
- opcode 249 / `rs/o/a/a/a/H` / 000720 -> `SpellOnPlayerPacket`

The exact router table also contains spell-on-object opcode 35; that generated class is
absent from this packet-object family.

## Boundary

These names describe transport targeting only. They do not claim that a particular item or
spell is valid for the target or define any server-side effect.

R326 remains non-canonical semantic research only.

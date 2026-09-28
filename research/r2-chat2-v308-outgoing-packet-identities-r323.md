# Chat 2 — exact-v308 outgoing packet identities R323

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R322 corrected the base contract to `OutgoingPacket`.

R323 names only concrete packet classes whose fixed opcode is independently identified by
the exact-current protocol corpus.

## Social packets

- `rs/o/a/a/a/a` / 000687 / opcode 188 -> `AddFriendPacket`
- `rs/o/a/a/a/b` / 000688 / opcode 133 -> `AddIgnorePacket`
- `rs/o/a/a/a/j` / 000696 / opcode 215 -> `RemoveFriendPacket`
- `rs/o/a/a/a/k` / 000697 / opcode 74 -> `RemoveIgnorePacket`

All four classes contain exactly one long payload and write it after the fixed opcode. The
exact protocol contracts define that long as the name hash.

## UI/input packets

- `rs/o/a/a/a/h` / 000694 / opcode 185 -> `WidgetActionPacket`
- `rs/o/a/a/a/i` / 000695 / opcode 130 -> `CloseInterfacePacket`
- `rs/o/a/a/a/m` / 000699 / opcode 208 -> `AmountInputPacket`

Opcode 185 is the generic widget-action route; opcode 130 is the no-payload interface-close
request; opcode 208 is the native amount-input i32 route.

## World/inventory packets

- `rs/o/a/a/a/N` / 000726 / opcode 132 -> `ObjectOption1Packet`
- `rs/o/a/a/a/X` / 000736 / opcode 214 -> `InventoryMovePacket`

The exact action matrix fixes C2S132 as object option 1 with objectId/worldX/worldY.
Independent production protocol evidence fixes C2S214 as inventory move.

## Withheld remainder

The rest of the 52 concrete classes are not bulk-named from opcode folklore. Context-sensitive
families (player/NPC/object/widget-item option slots, item/spell-on-target routes, etc.) will be
recovered only where exact-current protocol evidence fixes the transport contract.

R323 is non-canonical semantic research only.

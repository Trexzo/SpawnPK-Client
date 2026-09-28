# Chat 2 — NPC/object outgoing option packets R324

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R324 extends the corrected R322 `OutgoingPacket` family using only exact-current transport
slot identities.

## NPC option packets

- `rs/o/a/a/a/J` / 000722 / opcode 155 -> `NpcOption1Packet`
- `rs/o/a/a/a/c` / 000689 / opcode 72 -> `NpcOption2Packet`
- `rs/o/a/a/a/K` / 000723 / opcode 17 -> `NpcOption3Packet`
- `rs/o/a/a/a/L` / 000724 / opcode 21 -> `NpcOption4Packet`
- `rs/o/a/a/a/M` / 000725 / opcode 18 -> `NpcOption5Packet`

The exact-current protocol matrix defines the NPC option family as 1..5 ->
155/72/17/21/18.

R324 deliberately does not rename option 2 to Attack or option 1 to Talk-to: those are
contextual menu verbs, while the packet contract is the option slot.

## Object option packets

R323 already recovered option 1:

- opcode 132 -> `ObjectOption1Packet`

R324 adds:

- `rs/o/a/a/a/O` / 000727 / opcode 252 -> `ObjectOption2Packet`
- `rs/o/a/a/a/P` / 000728 / opcode 70 -> `ObjectOption3Packet`
- `rs/o/a/a/a/Q` / 000729 / opcode 234 -> `ObjectOption4Packet`
- `rs/o/a/a/a/R` / 000730 / opcode 228 -> `ObjectOption5Packet`

Again, the exact semantic is the object option slot; object-definition action text remains
context-dependent.

## Boundary

No player-option classes are included here because exact v308 contains duplicate generated
packet classes for opcodes 128 and 139 with identical serialization, leaving no defensible
basis to pick one duplicate as canonical semantic owner.

R324 remains non-canonical semantic research only.

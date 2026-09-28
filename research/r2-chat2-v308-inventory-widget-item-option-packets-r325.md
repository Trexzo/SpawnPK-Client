# Chat 2 — inventory/widget-item outgoing option packets R325

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Inventory-item options

- opcode 122 / `rs/o/a/a/a/Z` / 000738 -> `InventoryItemOption1Packet`
- opcode 16 / `rs/o/a/a/a/D` / 000716 -> `InventoryItemOption3Packet`
- opcode 75 / `rs/o/a/a/a/C` / 000715 -> `InventoryItemOption4Packet`
- opcode 87 / `rs/o/a/a/a/l` / 000698 -> `InventoryItemOption5Packet`

Opcode 41 is intentionally withheld: exact-current protocol authority records it both as
the normal inventory option-2 route and an option-1 equip alias. The generated class
`rs/o/a/a/a/n` cannot therefore be assigned one unqualified slot name safely.

## Widget-item options

- opcode 145 / `s` / 000705 -> `WidgetItemOption1Packet`
- opcode 117 / `t` / 000706 -> `WidgetItemOption2Packet`
- opcode 43 / `u` / 000707 -> `WidgetItemOption3Packet`
- opcode 129 / `v` / 000708 -> `WidgetItemOption4Packet`
- opcode 135 / `w` / 000709 -> `WidgetItemOption5Packet`

The generated family has no opcode-176 option-6 packet object.

## Naming boundary

These are transport-slot names only. Exact-current protocol research proves that visible
verbs are contextual: opcode 87 is not intrinsically Drop, opcode 41 is not intrinsically
Equip, and widget-item option slots can represent actions such as Buy amounts.

R325 remains non-canonical semantic research only.

# Chat 2 — exact-v308 item dialogue / ScriptPacket 33 R140

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R140 resolves the previously withheld ScriptPacket 33 family from exact root behavior,
Client continue-key handling and the embedded item-definition-backed content slot.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_5292A9349329C906DE45`
- field/method proposals: **0**

## Stable IDs

- `rs/n/c/a/a` -> `CLIENT_CLASS_000574` -> `ItemDialogueInterface`
- `rs/n/c/a/b` -> `CLIENT_CLASS_000575`
  -> `ItemDialogueInterfacePacketHandler`

## Exact dialogue-root identity

`rs/n/c/a/a` owns root:

**30700**

Client exact static state groups 30700 with roots:

- 4882;
- 4887;
- 4893;
- 4900.

When the active interface root is one of those five values, pressing **space** sends the same
continue action: packet opcode 40 with value **4907**.

That places root 30700 in the same explicit space-to-continue interface family rather than
the numeric-choice family.

## Exact multi-line composition

Root 30700 composes:

- text widget 6181;
- text widget 6182;
- text widget 6183;
- text widget 6184;
- widget 4892;
- content widget 14171.

ScriptPacket 33 can populate one, two, three or four Strings into 6181-6184.

The packet handler then adjusts the active line positions and finalizes the same root so
short and long dialogue text remains vertically arranged.

## Exact item content

Widget 14171 is configured through `rs/n/c/A.a(...)`.

That exact helper resolves:

`rs/d/k.f(itemId)`

and consumes model-scale information from that item definition when constructing the widget
content.

The default root build configures 14171 with item id **21235**, while ScriptPacket 33 can
replace its packet-controlled item/content values.

This fixes the safe class noun as an item-bearing dialogue interface.

The interface reuses a widget from the R129 `ConfirmationInterface` family for presentation,
but root 30700 itself belongs to the separate space-to-continue root set. R140 therefore does
not rename it as another confirmation prompt.

## ScriptPacket 33

The dispatcher registers the singleton field `rs/n/c/a/a.e` as ScriptPacket **33**.
The exact static initializer constructs `rs/n/c/a/b` into that field.

Its modes are coherent:

- **0** — rebuild/reset root 30700;
- **1** — configure the item/content slot;
- **2** — write one through four dialogue Strings and reflow their layout;
- **3** — emit same-screen presentation particles;
- **4** — reset/reflow the item-dialogue layout.

No mode mutates an unrelated gameplay subsystem.

## Naming boundary

`ItemDialogueInterface` is **0.998**.
`ItemDialogueInterfacePacketHandler` is **0.999**.

R140 does not claim a reward, unlock, loot or specific NPC domain. Those would be plausible
uses, but exact v308 only proves item-backed, multi-line, space-to-continue dialogue behavior.

## Residual ScriptPacket boundary

After R140, the deliberately unnamed ScriptPacket frontier falls to three IDs:

- **8** — combat-stat-like overlay, higher-level feature noun still not proven;
- **27** — twelve-string overlay with no self-identifying content domain;
- **32** — mixed handler with no honest single subsystem noun.

## Acceptance boundary

Chat 2 does not promote R140. Main/Core may accept either proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_5292A9349329C906DE45`.

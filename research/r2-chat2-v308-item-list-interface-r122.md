# Chat 2 — exact-v308 item-list interface / ScriptPacket 14 R122

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R122 is a separate non-canonical class-only review for the item-list/search interface
subsystem and its direct R115 ScriptPacket handler.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_761085F0BAEBCC13F99B`
- field/method proposals: **0**

## Stable IDs

- `rs/n/c/ac` -> `CLIENT_CLASS_000604` -> `ItemListInterface`
- `rs/q/a/a/a/h` -> `CLIENT_CLASS_000753`
  -> `ItemListInterfacePacketHandler` — ScriptPacket **14**

## ItemListInterface

Exact v308 builds the interface rooted at **36000**.

The builder preserves explicit item-list vocabulary:

- `Item List Title`;
- `Description Line 1`;
- `Description Line 1 (small)`;
- five tab controls;
- `Select tab`;
- `Search by item`;
- `<img=39> Search for an item`;
- `Search description text`;
- `Go back`.

Its visual resources include:

- `list/bg`;
- `list/bg top`;
- `list/bg bottom`;
- `list/bg foot`.

The interface also installs exact item transfer actions:

- `Remove 1`;
- `Remove 5`;
- `Remove 10`;
- `Remove All`;
- `Deposit 1`;
- `Deposit 5`;
- `Deposit 10`;
- `Deposit All`;
- `Deposit all to bank`;
- `Deposit all to inventory`.

It creates the scroll/list region, list entry widgets, tab labels, search controls,
description lines and bank/inventory transfer buttons. Static methods on the same class
control list contents, tabs, search state, descriptions, visibility and selection.

That gives a direct exact-v308 identity as an item-list/search interface subsystem.

## ScriptPacket 14 — ItemListInterfacePacketHandler

R115 registers `rs/q/a/a/a/h` as ScriptPacket **14**.

The handler has a 26-way selector. Unlike the mixed ScriptPacket 32 handler, these modes are
coherent around one subsystem.

They dispatch into `ItemListInterface` methods or mutate its exact 36000-series widgets
to perform operations including:

- reset/open/close list state;
- select or configure tabs;
- enable/disable list/search modes;
- populate item rows;
- set title and description text;
- update search text/results;
- update list geometry/layout;
- control list visibility and current selection.

The handler therefore has a defensible subsystem noun only after the target
`ItemListInterface` is recovered alongside it.

## Naming boundary

Neither English name is claimed as a surviving original SpawnPK identifier.

`ItemListInterface` is descriptive at **0.997**.
`ItemListInterfacePacketHandler` is **0.998** because R115 additionally fixes the exact
ScriptPacket registration and every selector targets the recovered interface subsystem.

R122 remains class-only.

## Deliberate exclusion

ScriptPacket 32 (`rs/q/a/a/a/a`) remains unnamed. One mode explicitly switches Blood and
Infernal spell widget names/sprites, but the class also mutates unrelated Client fields,
strings and toggles. There is still no honest single subsystem noun for the whole class.

## Acceptance boundary

Chat 2 does not promote R122. Main/Core may accept either proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_761085F0BAEBCC13F99B`.

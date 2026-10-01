# Chat 2 — exact-v308 server selection interface R452

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/n/c/aM` -> `CLIENT_CLASS_000588` -> `ServerSelectionInterface`
- `rs/n/c/aN` -> `CLIENT_CLASS_000589` -> `ServerSelectionInterfacePacketHandler`
- review: `SEMREVIEW_5CAF37C520A6BE4F2AC0`

## Exact protocol join

The live ScriptPacket dispatcher registers `rs/n/c/aM.c` as subtype **16**.

Independent exact-current protocol authority identifies ScriptPacket 16 as the
**server selection list**.

## Interface behavior

`aM` builds a 50-row scroll/list surface around root **40403** / scroll **40404**.

It supports:

- selectable rows with exact tooltip `Select`;
- non-selectable rows;
- per-row text updates;
- dynamic row insertion;
- scroll-height maintenance;
- complete reset of row state.

## Handler behavior

`aN` is the exact ScriptPacket-16 handler.

Its selector surface is fully bounded to the same interface:

- selector 0 — reset list/counters and clear all 50 rows;
- selector 1 — append one row from packet metadata + text;
- selector 2 — update one indexed row's text.

## Boundary

This recovers client presentation/state transport only. Server discovery, availability,
selection validation and connection authority remain outside this semantic layer.

R452 remains non-canonical Chat 2 research only.

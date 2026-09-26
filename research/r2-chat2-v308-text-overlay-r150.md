# Chat 2 — exact-v308 TextOverlay / ScriptPacket 27 R150

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R150 is a separate non-canonical class-only review for the final unnamed direct
twelve-string overlay protocol identified as ScriptPacket **27**.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_8C2F40C36F433BC19E4A`
- field/method proposals: **0**

## Stable IDs

- `rs/l/f/a/h/a` -> `CLIENT_CLASS_000467` -> `TextOverlay`
- `rs/l/f/a/h/b` -> `CLIENT_CLASS_000468` -> `TextOverlayPacketHandler`

## Exact client structure

`TextOverlay` is constructed by the live overlay manager and registered as an
`rs/l/f/b` overlay.

It owns exactly **twelve nullable String fields**.

The renderer lays those values out as four spatial groups:

- three centered/right-side lines;
- three bottom/right-side lines;
- three bottom/left-side lines;
- three top/left-side lines.

The class has one reset operation that clears all twelve values together, plus one setter for
each text slot.

No surviving literal gives a more specific gameplay noun.

## ScriptPacket 27

R115 registers `rs/l/f/a/h/b` directly as ScriptPacket **27**.

Its packet shape exactly mirrors the overlay:

- selector **0** clears all twelve text fields;
- selectors **1–4** choose one of the four overlay groups;
- a second packet integer **1–3** selects one field within that group;
- one packet String becomes the selected overlay text.

The handler writes only to `TextOverlay`.

There is no second subsystem branch.

## Independent server-producer corroboration

The preserved `SpawnPK-Src-Git-207a8fe.zip` snapshot exposes the corresponding application
protocol in `ApplicationUiService` as:

- `overlayTextClear(...)`;
- `overlayTextField(..., group, field, text)`.

The producer enforces group **1–4** and field **1–3**, then emits ScriptPacket **27**.

This is secondary corroboration rather than a replacement for exact-v308 client authority,
but its terminology and shape independently match the client bytecode exactly.

## Naming boundary

`TextOverlay` and `TextOverlayPacketHandler` are descriptive at **0.999**.

The protocol noun `overlayText` survives in the preserved server-side producer, while the
exact client independently fixes the complete live overlay and packet shape.

Neither name is claimed as a surviving original client source identifier.

## Remaining ScriptPacket frontier

After R150, the only deliberately unnamed ScriptPacket handler remains **32**
(`rs/q/a/a/a/a`).

Its producer is described as custom-magic presentation in the preserved server snapshot, but
the exact client handler still mutates several broad Client fields in addition to spell
widgets. It remains withheld until those fields can be tied independently to one coherent
custom-magic presentation responsibility.

## Acceptance boundary

Chat 2 does not promote R150. Main/Core may accept either proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_8C2F40C36F433BC19E4A`.

# Chat 2 — exact-v308 generic status/progress overlay R318

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Proposed recovery

- `rs/l/e/a/m` -> `CLIENT_CLASS_000411` -> `StatusProgressOverlay`
- `rs/l/e/a/n` -> `CLIENT_CLASS_000412` -> `StatusProgressOverlayStateHandler`
- review: `SEMREVIEW_645E359560E8991081F3`

## Overlay behavior

`rs/l/e/a/m` extends R111 `ClientOverlay`.

Its render surface is a fixed top-screen status box approximately 220x40 pixels. It draws:

- background/border rectangles;
- a horizontal progress bar;
- centered String state;
- a right-side String state;
- percentage text.

The fill width is derived from:

`ceil((percentage / 100.0) * barWidth)`

The overlay owns an explicit active boolean and returns that value from its visibility predicate.

It initializes/reset state including:

- progress text `100%`;
- two bar colors;
- percentage 0;
- empty centered text.

## Cross-overlay layout behavior

R201 `CombatOverlay` returns no dimensions / suppresses itself while this overlay is active.

R112 `WorldCoordinateOverlay` adds vertical spacing when this overlay is active.

Those independent consumers prove that the object occupies a live shared top-screen
status/progress slot, but they do not identify a narrower product feature.

## State handler

`rs/l/e/a/n` extends R115 `ScriptPacketHandler`.

Its selector surface writes only the StatusProgressOverlay singleton:

1. reset state and toggle activation;
2. set the two bar colors;
3. no-op;
4. read current/max, compute percentage and build
   `current / max @yel@(percent%)`;
5. set centered String;
6. set right-side String to `<img=305><value>`.

## Important dormant-dispatch boundary

The exact-v308 R115 dispatcher registers ScriptPacket IDs 1..43.

It does **not** register:

- `rs/l/e/a/n`;
- `rs/l/e/a/m.F`;
- any direct class alias resolving to this handler.

The handler is therefore present and packet-shaped in exact v308 but is not claimed as an
active registered ScriptPacket endpoint.

This is why the proposed name is `StatusProgressOverlayStateHandler`, not an asserted live
ScriptPacket ID-specific name.

## Boundary

No feature-specific noun is invented. R318 remains non-canonical semantic research only.

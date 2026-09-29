# Chat 2 — ScriptPacket target interfaces R375

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/n/c/J` -> `CLIENT_CLASS_000555` -> `EventActivityViewerInterface`
- `rs/n/c/O` -> `CLIENT_CLASS_000561` -> `ActiveEventsInterface`
- `rs/n/c/V` -> `CLIENT_CLASS_000568` -> `GamblingInterface`
- `rs/n/c/ag` -> `CLIENT_CLASS_000608` -> `ItemsKeptOnDeathInterface`
- `rs/n/c/aq` -> `CLIENT_CLASS_000621` -> `MakeQuantityInterface`
- review: `SEMREVIEW_92EE8B56E756977B05B4`

## Why this batch is safe

R127 already recovered the five corresponding ScriptPacket-side handlers:

- EventActivityViewerInterfacePacketHandler
- ActiveEventsInterfacePacketHandler
- GamblingInterfacePacketHandler
- ItemsKeptOnDeathInterfacePacketHandler
- MakeQuantityInterfacePacketHandler

Those reviews fixed each handler to exactly one target interface class and one bounded
widget/state surface.

R375 completes the other side of those already-proven pairs.

## Exact self-identifying surfaces

`rs/n/c/J` preserves:

- `Event Activity Viewer`
- token-limit / activity-lock strings.

`rs/n/c/O` preserves:

- `View Active Events`
- `View all events`
- Event Global Boss / Event Wildy Boss state.

`rs/n/c/V` preserves:

- `gambling/SPRITE`
- Accept / Decline offer controls
- `Gambling with P1..`
- game-type selection and gambling rules.

`rs/n/c/ag` preserves:

- `Items kept on death`
- keep / lose / auto-keep sections.

`rs/n/c/aq` preserves:

- `How many would you like to make?`
- 1 / 5 / 10 / X / All quantity controls
- `options/make/sprite` resources.

## Boundary

R375 remains class-only, non-canonical semantic research. No semantic acceptance, source
rewrite or release mutation is performed.

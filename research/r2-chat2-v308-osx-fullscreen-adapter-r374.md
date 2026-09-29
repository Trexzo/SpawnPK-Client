# Chat 2 — OSX fullscreen adapter R374

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/A/n` -> `CLIENT_CLASS_000017` -> `OSXFullScreenAdapter`
- proposal: `SEMPROP_DFCFE84222B5E2FC5D19`
- review: `SEMREVIEW_696BA78E6F64358466A3`

## Exact-v308 behavior

The class:

- extends `com.apple.eawt.FullScreenAdapter`;
- owns the target `java.awt.Frame`;
- registers through `FullScreenUtilities.addFullScreenListenerTo`;
- on fullscreen entry logs the transition and sets `Frame.MAXIMIZED_BOTH`;
- on fullscreen exit logs the transition and restores `Frame.NORMAL`.

The exact log strings are:

- `Window entered fullscreen mode--setting extended state to {}`
- `Window exited fullscreen mode--setting extended state to {}`

## Historical source identity

RuneLite-derived historical sources preserve the standalone class name:

`OSXFullScreenAdapter`

with the same superclass, frame field, static registration helper, log strings and
extended-state transitions.

This is therefore source-name recovery, not merely a descriptive semantic label.

## Boundary

R374 is non-canonical semantic research only. Chat 2 does not perform acceptance or source rewrite.

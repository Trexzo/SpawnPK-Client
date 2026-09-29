# Chat 2 — exact-v308 client window layout task R394

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/l/D` -> `CLIENT_CLASS_000353` -> `ClientWindowLayoutTask`
- proposal: `SEMPROP_1CC9DF0459B2037C0A30`
- review: `SEMREVIEW_B1FDC3EB869816E4B538`

## Exact ownership

R85 already fixed `rs/l/C` as `DepthBufferedImageSurface`.

Its live draw method schedules `rs/l/D` exactly once through:

`SwingUtilities.invokeLater(...)`

after the first framebuffer image blit, under a static one-shot guard.

No other exact-v308 class constructs `rs/l/D`.

## Exact behavior

The Runnable obtains the Launcher JFrame and applies top-level client-window layout:

- normal dimensions: **1134 x 537**
- alternate/larger layout: **1312 x 800**
- makes the frame visible when the larger shell mode is active
- centers the frame using Toolkit screen dimensions
- conditionally maximizes when the larger requested width exceeds available screen width

The task does not touch framebuffer data itself; it is deferred window-shell layout work
triggered by the first live depth-buffered surface draw.

## Boundary

The name is descriptive exact-v308 behavior only. It does not claim an original stripped
developer identifier.

R394 remains non-canonical semantic research only.

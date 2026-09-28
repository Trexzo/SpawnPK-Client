# Chat 2 — glow and motion text effects R357

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/l/m` -> `CLIENT_CLASS_000502` -> `GlowTextEffect`
- `rs/l/s` -> `CLIENT_CLASS_000510` -> `TextMotionEffect`
- review: `SEMREVIEW_75098DE0E3D7EF3D9112`

## GlowTextEffect

The exact font pipeline recognizes `@glo@` and numbered glow variants. The class advances
a phase every 40 ms and combines phase + character position against eight precomputed
256-step color palettes.

The resulting color is applied per character by R55 `RSFont`.

## TextMotionEffect

Exact controls include:

- `@hov@`
- `@shi@`
- `<hover>` / `</hover>`
- `<shift>` / `</shift>`
- `<lift=N>` / `</lift>`

Hover/shift produce sinusoidal pixel offsets. Lift applies a signed parsed vertical offset,
clamped to 40 pixels. RSFont applies these offsets to glyphs and inline visual elements.

Animated motion also marks a short redraw lifecycle so the effect continues updating.

R357 remains non-canonical semantic research only.

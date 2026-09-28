# Chat 2 — exact-v308 GPU startup world-load task R338

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/k/f` -> `CLIENT_CLASS_000335` -> `GpuStartupWorldLoadTask`
- proposal: `SEMPROP_F79B197C8E86F3EE667B`
- review: `SEMREVIEW_999D7A8D27FC00D7949B`

R87 already identifies `rs/k/e` as `GpuRenderer`.

During GPU startup, when the live client is already in its logged-in/active state, GpuRenderer
constructs this Runnable and schedules it through the renderer's client-thread helper.

The task:

1. puts the canvas/client into the GPU repaint state;
2. when compute mode is not NONE, rebuilds the retained GPU scene/buffer state;
3. performs the renderer GL error check;
4. invokes the client refresh/redraw path.

Independent upstream RuneLite GPU source preserves the same startup markers
(`canvas.setIgnoreRepaint(true)`, exact diagnostic `Error starting GPU plugin`) and
explicitly calls `startupWorldLoad()` when the client is already `LOGGED_IN`.

The sibling `rs/k/g` is only the compiler-generated enum-switch map over compute mode and
remains excluded.

R338 remains non-canonical semantic research only.

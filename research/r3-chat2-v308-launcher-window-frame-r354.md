# Chat 2 R3 — launcher window frame/resize policy R354

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/gui/u` -> `CLIENT_CLASS_000281` -> `LauncherWindowFrame`
- `rs/gui/v` -> `CLIENT_CLASS_000283` -> `LauncherResizePolicy`
- review: `SEMREVIEW_BDEF4370C20AF043CE57`

## LauncherWindowFrame

The class directly extends `JFrame`. Launcher owns exactly one instance in its active
window field and exposes the same frame through its window accessor.

The frame owns:

- monitor-aware location/bounds clamping;
- maximize bounds;
- width changes associated with the launcher's side-panel/game area;
- window/game-size preservation behavior.

It contains no packet/gameplay domain state.

## LauncherResizePolicy

The enum has exactly two values and display strings:

- `KEEP_WINDOW_SIZE` -> `Keep window size`
- `KEEP_GAME_SIZE` -> `Keep game size`

LauncherWindowFrame branches directly on these values when applying width changes.

R354 is descriptive non-canonical semantic research only.

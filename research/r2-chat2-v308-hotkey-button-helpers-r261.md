# Chat 2 — exact-v308 HotkeyButton helper family R261

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic review result

- `rs/s/b/j` -> `CLIENT_CLASS_000870` -> `HotkeyButtonResetMouseListener`
- `rs/s/b/k` -> `CLIENT_CLASS_000871` -> `HotkeyButtonKeyCaptureListener`
- review: `SEMREVIEW_1B87AA177201CCB86A8B`
- unresolved: **0**
- field/method proposals: **0**

## Exact behavior

R237 already recovers `rs/s/b/i` as `HotkeyButton` and `rs/s/b/l` as `Keybind`.

### Reset mouse listener

`rs/s/b/j` extends `MouseAdapter`. Its only event method is
`mouseReleased`.

When the released button is the left mouse button, it assigns the reviewed
`Keybind.NOT_SET` singleton to its owned `HotkeyButton`.

### Key-capture listener

`rs/s/b/k` extends `KeyAdapter`. It owns one `HotkeyButton` plus the constructor's
boolean capture-mode flag.

Its only event method is `keyPressed`: exact v308 constructs a `Keybind` from the
incoming `KeyEvent` and assigns that binding to the owned button.

The optimizer preserves two control-flow branches around the capture-mode flag, but both
surviving bytecode branches resolve to the same reviewed Keybind constructor. R261 therefore
does not claim more mode-specific behavior than exact v308 proves.

## Naming boundary

Both R261 names are descriptive exact-behavior names for anonymous listener classes. They
do not claim verbatim original source identifiers.

## Acceptance boundary

R261 remains class-only and non-canonical. Chat 2 performs no semantic acceptance.

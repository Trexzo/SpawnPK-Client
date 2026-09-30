# Chat 2 continuation — Launcher frame/client host helpers R335

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/gui/C` -> `CLIENT_CLASS_000186` -> `LauncherFrameResizableTask`
- `rs/gui/D` -> `CLIENT_CLASS_000187` -> `LauncherFrameSizeTask`
- `rs/gui/E` -> `CLIENT_CLASS_000188` -> `ClientCanvasHostPanel`
- review: `SEMREVIEW_D1590A0DCE0671141200`

## Frame resizable task

Launcher schedules `rs/gui/C` through `SwingUtilities.invokeLater`.

The Runnable owns one boolean and applies it directly through
`Launcher.i().setResizable(boolean)`.

## Frame size task

`rs/gui/D` owns four integer dimensions and the Launcher.

Its run method sets:

1. JFrame minimum size from the first width/height pair;
2. JFrame current size from the second pair.

## Client canvas host

`rs/gui/E` extends JPanel, uses the Launcher client dimension, BorderLayout and a black
background.

Launcher constructs the live `Client`, initializes/starts it, then adds it to this panel
with `BorderLayout.CENTER`. The panel is then inserted into the main Swing content surface
beside the optional ClientSidebarPanel.

## Withheld sibling

`rs/gui/F` overrides paintComponent but performs no behavior beyond the JPanel superclass
call in exact v308, so it remains unnamed.

R335 remains non-canonical semantic research only.

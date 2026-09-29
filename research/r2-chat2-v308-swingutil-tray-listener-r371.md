# Chat 2 — SwingUtil tray-icon listener R371

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/gui/N` -> `CLIENT_CLASS_000198` -> `SwingUtilTrayIconMouseListener`
- proposal: `SEMPROP_674FE1C5ECF8CA25B963`
- review: `SEMREVIEW_2D19B4E5F7CAAED279C7`

R180 already fixes `rs/gui/M` as source-proven `SwingUtil`.

## Exact-v308 ownership

`SwingUtil.createTrayIcon(...)` constructs exactly one `rs/gui/N` and immediately registers
it via `TrayIcon.addMouseListener`.

No other exact-v308 class constructs the listener.

## Exact click behavior

The listener stores only the target `Frame`.

On click it:

1. checks the OS helper;
2. on the macOS branch, if the frame is not focused, hides the frame and invokes the
   macOS foreground helper;
3. makes the frame visible;
4. restores the frame to `Frame.NORMAL`.

## Historical source match

Historical RuneLite-derived source:

`Jire/tarnish@a4796be8e8cdef2398faf1081fa6a4da8a0190b1`

`game-client/src/main/java/net/runelite/client/util/SwingUtil.java`

contains the same anonymous `MouseAdapter` inside `createTrayIcon`, including the same
macOS visibility/focus workaround and final frame restore.

Because the original source construct is anonymous, R371 uses a descriptive generated-class
name rather than claiming a nonexistent standalone source identifier.

R371 remains non-canonical semantic research only.

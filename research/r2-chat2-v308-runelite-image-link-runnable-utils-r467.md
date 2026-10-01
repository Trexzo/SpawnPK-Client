# Chat 2 — exact-v308 RuneLite image/navigation/runnable utilities R467

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/A/j` -> `CLIENT_CLASS_000013` -> `ImageUtil`
- `rs/A/l` -> `CLIENT_CLASS_000015` -> `LinkBrowser`
- `rs/A/r` -> `CLIENT_CLASS_000023` -> `RunnableExceptionLogger`
- review: `SEMREVIEW_4B167B8F1C77FEBDE073`

All three identities are corroborated directly against RuneLite source.

## ImageUtil

Exact v308 preserves the broad image helper surface: classpath image loading through
ImageIO, Image->BufferedImage/ARGB conversion, resizing, aspect-preserving scaling,
horizontal/vertical flipping and other shared BufferedImage transforms.

It also preserves the exact load-failure log text:

`Failed to load image from class: {}, path: {}`

This matches RuneLite `net.runelite.client.util.ImageUtil`.

## LinkBrowser

Exact v308 has the same URL/folder navigation flow as RuneLite LinkBrowser:

- Linux xdg-open attempt;
- Desktop browse/open fallback;
- warning/debug logging;
- Swing fallback dialog;
- copy URL/folder to clipboard when navigation fails.

The class literally logs `LinkBrowser.browse()` and `LinkBrowser.open()`.

## RunnableExceptionLogger

Exact v308 wraps one Runnable, invokes it, catches Throwable, logs:

`Uncaught exception in runnable {}`

then rethrows the failure. It also exposes the same static wrap factory.

This matches RuneLite `net.runelite.client.util.RunnableExceptionLogger`.

## Boundary

R467 is non-canonical semantic research only.

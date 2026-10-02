# Chat 2 — client bounds and game clocks R376

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/g/a` -> `CLIENT_CLASS_000177` -> `ClientBounds`
- `rs/g/b` -> `CLIENT_CLASS_000180` -> `GameClock`
- `rs/g/c` -> `CLIENT_CLASS_000181` -> `MillisGameClock`
- `rs/g/d` -> `CLIENT_CLASS_000182` -> `NanoGameClock`
- review: `SEMREVIEW_EFABA243C5D04E05F260`

`rs/C.aZ()` reads the active AWT container dimensions, subtracts window insets when present and returns ClientBounds.

`rs/C` stores one GameClock and calls its pacing method from the main loop. `rs/C.be()` prefers NanoGameClock and falls back to MillisGameClock on Throwable.

MillisGameClock uses a ten-sample currentTimeMillis history, adaptive cycle ratio and sleep interval. NanoGameClock uses nanoTime deadlines and high-resolution pacing.

R376 is non-canonical semantic research only.

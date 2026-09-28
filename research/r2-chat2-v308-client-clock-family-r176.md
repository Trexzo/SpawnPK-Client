# Chat 2 — exact-v308 client clock family R176

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Source-name correction

This revision supersedes the earlier descriptive clock names with the stronger historical
RuneScape identities recovered from the exact hierarchy:

- `rs/g/b` -> `CLIENT_CLASS_000180` -> `Clock`
- `rs/g/c` -> `CLIENT_CLASS_000181` -> `MilliClock`
- `rs/g/d` -> `CLIENT_CLASS_000182` -> `NanoClock`
- `rs/g/e` -> `CLIENT_CLASS_000183` -> `SleepUtil`

Review: `SEMREVIEW_AD7D3B772B7FE26D3F4A`

The first three are source-proven legacy identities rather than descriptive aliases.
`SleepUtil` remains the existing exact-behavior descriptive name for the shared millisecond
sleep helper.

The base client stores `Clock`, prefers `NanoClock`, and falls back to `MilliClock`.
The latter preserves the classic ten-entry millisecond timing history; the former uses
`System.nanoTime()` and capped catch-up scheduling.

R176 remains non-canonical semantic research only.

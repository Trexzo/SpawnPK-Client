# Chat 2 — exact-v308 client clock hierarchy R357

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/g/b` -> `CLIENT_CLASS_000180` -> `Clock`
- `rs/g/c` -> `CLIENT_CLASS_000181` -> `MilliClock`
- `rs/g/d` -> `CLIENT_CLASS_000182` -> `NanoClock`
- review: `SEMREVIEW_95660E693BA83C7CD099`

## Game-loop factory

The AWT client base `rs/C` stores the active timer through the abstract `rs/g/b` type.

Its factory attempts:

1. `new rs/g/d()`;
2. on Throwable, falls back to `new rs/g/c()`.

The resulting Clock is called on every main game-loop iteration to determine how many client
cycles should be processed.

## MilliClock

`rs/g/c` has the long-standing RuneScape MilliClock structure:

- ten-entry long timestamp history;
- initial rate 256;
- minimum sleep step 1;
- currentTimeMillis-backed timing with backwards-clock compensation;
- adaptive rate/sleep calculation;
- returned cycle count.

Public RuneScape/OpenOSRS deobfuscations preserve this exact structural family under
`Clock -> MilliClock`.

## NanoClock

`rs/g/d` is the preferred high-resolution implementation:

- `System.nanoTime()` timing;
- nanosecond deadline advancement;
- sleeps when ahead;
- computes due client cycles;
- caps catch-up cycles at ten.

SpawnPK has local logic around active-client state, but the timing hierarchy identity remains
unambiguous.

## Boundary

`rs/g/e` is a standalone sleep helper but its original class-level identity is not
independently fixed, so R357 deliberately leaves it unnamed.

R357 remains non-canonical semantic research only.

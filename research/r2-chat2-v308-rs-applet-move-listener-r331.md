# Chat 2 continuation — RSApplet move listener R331

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/D`
- stable ID: `CLIENT_CLASS_000029`
- semantic: `RSAppletComponentMoveListener`
- review: `SEMREVIEW_D88D49F93F75009319DF`

## Exact ownership

R48 already fixes:

- `rs/C` -> `RSApplet`
- `rs/E` -> `RSFrame`

During listener initialization, RSApplet adds itself as the normal ComponentListener and then
constructs a second listener:

`new rs/D(this)`

That object is installed on the same Component.

## Exact behavior

`rs/D` extends `ComponentAdapter` and overrides only `componentMoved`.

On movement it:

1. compares current time against `Client.j`;
2. requires a gap greater than 100 ms;
3. sets `Client.h = true`;
4. stores the current timestamp back into `Client.j`.

No resize, focus, keyboard, mouse or rendering behavior exists in this helper.

## Boundary

The semantic name stops at component movement. R331 does not infer or rename the downstream
meaning of `Client.h` / `Client.j`.

R331 remains non-canonical semantic research only.

# Chat 2 — client component move listener R332

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/D` -> `CLIENT_CLASS_000031` -> `ClientComponentMoveListener`
- proposal: `SEMPROP_53DBA649CA4B4389CC0B`
- review: `SEMREVIEW_F8F8ABA22C4D9A92D585`

## Exact Java contract

`rs/D` extends `java.awt.event.ComponentAdapter`.

It overrides exactly one callback:

`componentMoved(ComponentEvent)`

No resize, focus, mouse, key or window callback exists in the class.

## Exact client installation

R48 already fixes `rs/C` as `RSApplet`.

During its component/listener setup, RSApplet constructs exactly one `rs/D(this)` and
installs it with `addComponentListener` on the active client drawing component.

## Move debounce

On component movement the listener compares `System.currentTimeMillis()` against the last
recorded move timestamp.

When more than 100 ms have elapsed it:

- sets the shared client relocation/layout invalidation flag;
- records the current timestamp.

The proposed name intentionally stops at the Java/input role and does not invent a more
specific downstream meaning for that global invalidation flag.

## Stable ID proof

Canonical `seed_lineage()` sorts the exact baseline by `internal_name` and assigns IDs
from ordinal 1.

Recomputing that rule against the exact v308 JAR gives:

- `rs/C` -> 000028
- `rs/Client` -> 000029
- `rs/Client$a` -> 000030
- `rs/D` -> 000031
- `rs/E` -> 000032

R332 remains non-canonical semantic research only.

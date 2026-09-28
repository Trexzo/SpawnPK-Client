# Chat 2 — exact-v308 PK Ratings interface / ScriptPacket 16 R131

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R131 resolves another interface through the exact route-to-root method used by R8 rather
than by neighboring package names.

R131 remains a separate non-canonical class-only review.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_7FE5D78DE62940533EAE`
- field/method proposals: **0**

## Stable IDs

- `rs/n/c/aM` -> `CLIENT_CLASS_000588` -> `PkRatingsInterface`
- `rs/n/c/aN` -> `CLIENT_CLASS_000589`
  -> `PkRatingsInterfacePacketHandler`

## Exact route-to-root authority

R8 `GameframeNavigationInterface` proves exact navigation:

`PK Ratings -> 40403`

`rs/n/c/aM.a()` directly creates root **40403**.

The builder also:

- attaches the shared gameframe/navigation shell;
- creates scroll/list widget **40404**;
- initializes row widgets beginning at **40405**;
- allocates exactly **50** list rows;
- uses exact row action text `Select`;
- lays the rows vertically in the list container.

That is sufficient to identify the root content interface as the PK Ratings destination,
using the same parent-route join principle as R8's Account Information recovery.

## ScriptPacket 16

R115 registers ScriptPacket **16** from `rs/n/c/aM.c`.

Exact v308 initializes that field with:

`new rs/n/c/aN()`

The complete handler selector surface is:

- **0**: reset list counters/state and clear the 50 widgets from **40405** upward;
- **1**: read row/type information, selectable flag and row String, then delegate the row
  into `rs/n/c/aM.b(...)`;
- **2**: read one row index and one String, then update that row through
  `rs/n/c/aM.k(...)`.

No selector mutates another Client subsystem.

## Naming boundary

`PkRatingsInterface` is descriptive readable recovery from the exact
`PK Ratings -> 40403` navigation join, not an original source-identifier claim.

Its confidence is **0.995**, matching the route-to-root evidence style used in R8.

`PkRatingsInterfacePacketHandler` is **0.998** because exact ScriptPacket registration and
the complete selector surface additionally bind it exclusively to that interface.

## Acceptance boundary

Chat 2 does not promote R131. Main/Core may accept either proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_7FE5D78DE62940533EAE`.

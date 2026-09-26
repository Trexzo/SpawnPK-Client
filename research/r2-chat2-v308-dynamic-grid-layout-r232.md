# Chat 2 — exact-v308 RuneLite DynamicGridLayout source recovery R232

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R232 recovers one standalone RuneLite UI source class.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_0B5B74A6D55CAADC04D6`
- field/method proposals: **0**

## Stable ID

- `rs/ui/j` -> `CLIENT_CLASS_001100` -> `DynamicGridLayout`

## Exact source identity

Exact v308 extends `java.awt.GridLayout` and preserves all three upstream constructors.
Its preferred/minimum sizing methods synchronize on the parent tree lock and feed a shared
dimension function into one helper. Layout computes dynamic row/column counts, scales child
preferred sizes to the parent dimensions, records maximum width per column and maximum
height per row, then assigns unequal cell bounds with the original inset/gap traversal.

RuneLite upstream `6e74752caa80fe9cb96cd9b37207e171fa525f07` contains
`net.runelite.client.ui.DynamicGridLayout` with the same implementation.

## Adjacent boundary

The nearby exact classes `rs/ui/d`, `rs/ui/g` and `rs/ui/h` are layout/window helper
classes attached to already-reviewed ClientTitleToolbar/ClientUI code, and `rs/ui/i` is a
compiler-generated switch table. R232 does not promote those helpers without a distinct
source-level identity.

## Acceptance boundary

Chat 2 does not promote R232. Main/Core may accept it only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_0B5B74A6D55CAADC04D6`.

# Chat 2 — exact-v308 event widget callbacks R317

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/l/e/a/j` -> `CLIENT_CLASS_000408` -> `HalloweenEventChestWidgetDecorationCallback`
- `rs/l/e/a/p` -> `CLIENT_CLASS_000414` -> `HalloweenHungerGamesWidgetDecorationCallback`
- review: `SEMREVIEW_FBD5A2286FE64BA4161F`
- member proposals: **0**

## Event Chest callback

R130 already fixed `rs/l/e/a/h` as `HalloweenEventChestOverlay`.

Its constructor registers one exact R314 widget-render callback:

- widget: **60612**
- callback: `rs/l/e/a/j`

The callback is a synthetic child of the overlay and implements `rs/l/e/i`.
When the parent overlay flag is active and `RSInterface.az[1] > 0`, it invokes the same
shared decoration renderer four times around the widget using fixed corner offsets.

No independent packet state or second owner exists.

## Halloween Hunger Games callback

R3 already fixed `rs/l/e/a/o` as `HalloweenHungerGamesOverlay`.

Its constructor registers one exact callback object across:

- 18038
- 18039
- 18040
- 18041
- 18042
- 18043
- 18044

The callback is `rs/l/e/a/p`, another synthetic implementation of R314
`InterfaceWidgetRenderCallback`.

It draws the parent overlay's shared `rs/l/F N` sprite relative to the widget position.
Widgets below 18041 use one fixed offset; widgets 18041+ use another.

The narrower meaning of the decoration sprite is not asserted.

## Naming boundary

Both names intentionally stop at **WidgetDecorationCallback**. Exact v308 proves callback
ownership, widget range and decoration rendering but does not preserve a safe noun such as
selection marker, border, highlight or badge.

R317 remains non-canonical semantic research only.

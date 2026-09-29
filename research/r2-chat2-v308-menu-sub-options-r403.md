# Chat 2 — exact-v308 dynamic menu sub-options R403

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/j/b/a` -> `CLIENT_CLASS_000308` -> `MenuSubOption`
- `rs/j/b/b` -> `CLIENT_CLASS_000309` -> `MenuSubOptionEntry`
- `rs/j/b/d` -> `CLIENT_CLASS_000312` -> `MenuSubOptionManager`
- review: `SEMREVIEW_7A05893FD6F77B9D7B0C`

## MenuSubOption

Stores one submenu title, its originating Client menu-row index, up to ten label/callback
entries, layout dimensions/position and current hovered entry.

Width is derived from exact client font measurements; height grows with entry count. The
object performs mouse hit-testing and exposes the selected entry.

## MenuSubOptionEntry

One entry contains exactly:

- String label
- invokable callback

No second domain responsibility exists.

## MenuSubOptionManager

The live manager:

- registers direct callbacks against Client menu rows;
- registers submenus against Client menu rows;
- inserts rows into the parallel Client menu arrays;
- supports first/last/current insertion placement;
- creates the exact default title `Choose Sub-Option`;
- activates submenus on the relevant row;
- invokes callbacks;
- clears transient maps;
- swaps complete menu rows while preserving callback ownership.

This is separate from R400 `DeferredMenuActionSnapshot`: R400 preserves one delayed action,
while R403 owns dynamic menu construction and submenu dispatch.

## Withheld class

`rs/j/b/c` exposes a plausible single-row text/callback binding API but has no exact-v308
external consumer beyond its own nested helper, so it remains intentionally unnamed.

R403 remains non-canonical semantic research only.

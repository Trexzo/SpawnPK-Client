# Chat 2 — rich-text markup and animated inline icons R343

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/l/a/a` -> `CLIENT_CLASS_000364` -> `AnimatedTextIconDefinition`
- `rs/l/j` -> `CLIENT_CLASS_000499` -> `RichTextMarkupRegistry`
- review: `SEMREVIEW_D0381A5F237736EE211B`

## AnimatedTextIconDefinition

Earlier research intentionally withheld `rs/l/a/a` because its nine integers were not
sufficient by themselves to fix a noun.

The exact consumer join now closes that gap.

Its constructor stores a start/end sprite range and initializes the current sprite frame.
The update method advances one frame and wraps to the start after the end.

`rs/l/j` registers explicit icon-id ranges including 21 -> 27..30, 32 -> 33..36,
45 -> 41..44 and several animated 333+ ranges.

R55 `RSFont` retrieves these definitions while parsing inline icons, chooses the current
Sprite from the text-icon sprite table, and consumes additional integers as icon
presentation offsets/spacing.

R74 `ItemIconOverlay` independently uses the same definition map for TEXT_ICON overlays.

## RichTextMarkupRegistry

`rs/l/j` owns:

- the AnimatedTextIconDefinition map;
- registered icon-id arrays/sets;
- markup color-name -> RGB mappings;
- classic color tokens such as red/gre/blu/cya/mag/whi/yel and shade variants;
- icon resource families including `icons/`, `clan/icons/` and popup icons;
- markup parsing/classification helpers;
- regex removal of classic `<...>` / `@...@` formatting.

The class is shared text/render infrastructure, not a font renderer itself.

## Boundary

Names describe exact-v308 behavior only. R343 remains non-canonical Chat 2 research.

# Chat 2 — exact-v308 ColorUtil R465

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/A/g` -> `CLIENT_CLASS_000010` -> `ColorUtil`
- proposal: `SEMPROP_0BF0157A3E49F911221D`
- review: `SEMREVIEW_839EB5D8B12E9743378B`

## Exact v308 surface

The utility owns:

- RuneScape color-tag generation and closing tags;
- text wrapping in a color tag;
- RGB and ARGB hex formatting/parsing;
- color interpolation;
- alpha replacement;
- hue/HSB transformations;
- RGB-range clamping.

Surviving literals include:

- `<col=`
- `>`
- `</col>`
- `%06x`
- `%08x`

and explicit RGB/ARGB hexadecimal validation patterns.

## Upstream identity

RuneLite `net.runelite.client.util.ColorUtil` carries the same shared color-helper role and
matching markup/constants/conversion surface.

The exact-v308 class is also consumed broadly across UI/plugin/rendering code, including
trading presentation, ground-marker/UI code and rich-text paths, which confirms it is not
feature-local.

## Boundary

R465 is non-canonical semantic research only. No member proposals or source rewrite are
performed.

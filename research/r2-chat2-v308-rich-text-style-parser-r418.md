# Chat 2 — exact-v308 rich-text style parser R418

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/l/i` -> `CLIENT_CLASS_000498` -> `OscillatingCounter`
- `rs/l/k` -> `CLIENT_CLASS_000500` -> `RichTextStyleParser`
- review: `SEMREVIEW_C3079120532AE3229ACE`

The lineage is contiguous with:

- R343 `rs/l/j` -> `RichTextMarkupRegistry` -> 000499
- R356 `rs/l/l` -> `FlashingTextEffect` -> 000501

## OscillatingCounter

The counter stores:

- fixed upper bound;
- current integer;
- direction step.

Each tick moves by one, flips direction at the upper bound, and flips positive again at zero.

RichTextStyleParser owns four counters bounded at 25, 50, 125 and 250. Client ticks all four
in its live update loop.

## RichTextStyleParser

R55 RSFont invokes this class throughout its markup parser.

Its methods recognize/delegate multiple rich-text style families including:

- pulse tags such as pu1 / pu2;
- flashing fla / fla2 state and closing forms;
- numeric and hexadecimal style parameters;
- inline item references;
- color/style reset and close tags;
- the separately reviewed rich-text effect and markup-registry helpers.

The class owns the animated style counters and coordinates the resulting values consumed by
RSFont during drawing.

## Boundary

This name is deliberately `RichTextStyleParser`, not `RichTextMarkupRegistry`: R343
already owns the registry of colors/icons/definitions, while R418 parses live tag text into
style/effect state.

R418 remains non-canonical semantic research only.

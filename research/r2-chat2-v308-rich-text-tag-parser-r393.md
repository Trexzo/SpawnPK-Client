# Chat 2 — rich-text tag parser and pulse counters R393

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/l/k` -> `CLIENT_CLASS_000500` -> `RichTextTagParser`
- `rs/l/i` -> `CLIENT_CLASS_000498` -> `RichTextPulseCounter`
- review: `SEMREVIEW_7C8F5C2BF1EAECC5ED33`

## RichTextTagParser

R55 `RSFont` calls this class throughout its markup scan.

Direct bytecode exposes tag families including:

- `pu1` / `pu2`
- `fla` / `fla2`
- `col`
- `trans`
- `shad`
- `u`
- `str`
- `tab`
- `yoff`

It also delegates already-recovered markup families to GlowTextEffect, TypewriterTextEffect,
TextParticleMarkup and InlineImageStyleMarkup.

This is distinct from R343 `RichTextMarkupRegistry`, which owns shared color/icon
definitions. R393's class performs per-string tag recognition and value parsing.

## RichTextPulseCounter

The companion state object is a bounded ping-pong integer counter.

RichTextTagParser owns four counters with bounds:

- 25
- 50
- 125
- 250

Client ticks all four during the live update path. The parser consumes their current values
for animated/pulsing rich-text color calculations.

R393 remains non-canonical Chat 2 semantic research only.

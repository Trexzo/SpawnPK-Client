# Chat 2 — text markup parser and oscillator R392

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/l/i` -> `CLIENT_CLASS_000498` -> `TextEffectOscillator`
- `rs/l/k` -> `CLIENT_CLASS_000500` -> `TextMarkupTagParser`
- review: `SEMREVIEW_641F4871AD329092FCE4`

## TextEffectOscillator

The class is a bounded ping-pong integer oscillator.

State:

- configured upper bound;
- current value;
- direction (+1 / -1).

Each tick advances current by direction, reverses at the upper bound, and reverses again at
zero.

The text-markup parser owns four instances with bounds:

- 25
- 50
- 125
- 250

Client advances all four once per live frame.

The 250-bound oscillator is read directly by the parser when generating a dynamic pulse
color.

## TextMarkupTagParser

R55 `RSFont` calls this class throughout inline markup parsing.

The exact tag vocabulary includes parser branches for:

- pulse-style color controls;
- `fla` / `fla2`;
- `item=`;
- color open/close controls;
- strike/style controls;
- `tab=`;
- `yoff=`;
- additional integer/sentinel text-render parameters.

The methods return parsed colors, ids, offsets, style values or sentinel values directly to
RSFont. The class owns no unrelated gameplay or networking state.

## Boundary

Names describe exact-v308 rendering behavior only and do not claim original stripped source
identifiers.

R392 remains non-canonical semantic research only.

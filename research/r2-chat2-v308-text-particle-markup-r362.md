# Chat 2 — text particle markup R362

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/l/t` -> `CLIENT_CLASS_000511` -> `TextParticleMarkup`
- proposal: `SEMPROP_D8B1415AE2008643B963`
- review: `SEMREVIEW_73AACF395992E2CC34D4`

## Exact markup

The RSFont path recognizes the particle controls:

- `@par@`
- `par` / numbered `par2..par8`
- `pimg` / numbered `p2img..p8img`

The class counts active particle controls, resolves the selected particle-image family and
selects up to three unique random palette/image variants. Selection is cached for 50 ms so
the same text span does not reshuffle every immediate layout/render pass.

## Particle emission

During drawing, RSFont calls the class with the current glyph/text rectangle and selected
particle state.

The class:

- randomizes a spawn position inside those bounds;
- constructs `rs/l/f/a/f/a`, the already-reviewed UI particle type;
- chooses direction/motion;
- assigns speed, size, alpha and randomized lifetime;
- registers the particle through the active UI particle manager.

This proves `par` means particle behavior, not generic parameter substitution.

The tiny `rs/l/u` LinkedHashMap implementation remains unnamed as a cache implementation
detail.

R362 remains non-canonical semantic research only.

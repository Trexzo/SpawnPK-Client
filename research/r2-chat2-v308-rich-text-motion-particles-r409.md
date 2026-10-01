# Chat 2 — rich-text motion and particle effects R409

Exact client authority: `854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

- `rs/l/s` -> `CLIENT_CLASS_000510` -> `RichTextMotionEffectProcessor`
- `rs/l/t` -> `CLIENT_CLASS_000511` -> `RichTextParticleEffectProcessor`
- review: `SEMREVIEW_2BD69559828DBB565369`

The motion processor parses hover/shift/lift tags. Its two sinusoidal helpers produce 2px and 3px offsets consumed directly by rs/l/h as rendered x/y offsets, while signed lift values (capped at 40) provide a static vertical displacement. A short redraw timer keeps animated content live.

The particle processor parses par/par2..par8 and pimg/pNimg markup. It selects palettes/styles, throttles repeat emission for the same string/position, constructs R204 OverlayParticle objects and submits them through OverlayParticleManager.

R409 is non-canonical semantic research only.

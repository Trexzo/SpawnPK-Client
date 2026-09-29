# Chat 2 — sprite transform and text-particle helpers R391

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/l/G` -> `CLIENT_CLASS_000356` -> `ColorKeyTransparencyFilter`
- `rs/l/H` -> `CLIENT_CLASS_000357` -> `ReferenceColorTransformFilter`
- `rs/l/L` -> `CLIENT_CLASS_000361` -> `SpriteColorTransformMath`
- `rs/l/u` -> `CLIENT_CLASS_000512` -> `TextParticleTimestampCache`

Review: `SEMREVIEW_B53EAE808A7C1A5351AD`

## Rendering filters

`rs/l/G` and `rs/l/H` are concrete RGBImageFilter helpers used by the already-reviewed
R55 `Sprite`.

The first performs exact color-key transparency. The second performs a coordinate-aware
reference-image color transform while preserving alpha.

## Sprite transform math

`rs/l/L` is stateless color math used only by R361 `SpriteStyleTransformer` for inline
image style transformations. It owns clamping and hue/saturation/value-like RGB operations,
not Sprite or markup state.

## Text-particle timestamp cache

`rs/l/u` is a bounded access-ordered `LinkedHashMap<Long,Long>` with a 512-entry cap.
R362 `TextParticleMarkup` uses it as a millisecond timestamp cache and suppresses
recomputation of particle selections inside a 50 ms window.

## Withheld neighboring classes

The unreviewed alignment parser `rs/l/x` and enum `rs/l/x$a` are currently unreferenced
in exact v308 and remain unnamed. Empty/dead direct classes are likewise withheld.

R391 remains non-canonical Chat 2 semantic research only.

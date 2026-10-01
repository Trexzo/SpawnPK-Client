# Chat 2 — R374–R390 duplicate semantic audit

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

R374 through R390 retain **no semantic proposals**.

The repository-wide class uniqueness gate showed that every class proposed in these batches
already had older Chat 2 semantic authority. The successor PR had rediscovered literal-rich
interfaces without first consulting the complete prior-review owner index.

Representative prior ownership:

- R374: `rs/n/c/Y` -> R8; `T` -> R5; `U` -> R2
- R375: `ag`/J/aq -> R5; O/V -> R2
- R376: `aw` -> R2
- R377: `rs/n/a/a/d` -> R19; `rs/n/a/a/a` -> R283
- R378: `rs/n/c/G` -> R2
- R379: `rs/n/c/ab` -> R2
- R380: `rs/n/c/b` and `a` -> R2
- R381: o/l -> R2; N -> R3
- R382: u -> R3
- R383: ba/n -> R5; m/p -> R2; q -> R3
- R384: k/j -> R5; aE -> R3; i -> R2
- R385: E/M -> R6; Z -> R3; F -> R5

The same audit proved the attempted R386–R390 interface batches were also entirely duplicate
ownership. Examples:

- `rs/n/c/A` -> R129
- `rs/n/c/D` -> R291
- `rs/n/c/H` -> R5
- `rs/n/c/I` and `aQ` -> R275
- `rs/n/c/aC`, aD, aI, aX, ad, c, h, s, ap -> R2
- `rs/n/c/aJ`, aK, aW, al, as, at, au, w -> R3
- `rs/n/c/aF`, ai, an, ao, az, aS, aZ -> R5
- `rs/n/c/aO`, aU, aj, af, g, ae, d -> R6
- `rs/n/c/ak` -> R137
- `rs/n/c/f` -> R136
- `rs/n/c/R` -> R286
- `rs/n/c/X` -> R295

## CI evidence

Recovery CI run `36506724870` failed the global uniqueness gate and explicitly reported
duplicate class owner `rs/n/c/Y: R8 and R374`, followed by the complete prior-owner map.

## Boundary

All R374–R390 candidate JSON, review JSON, tests and feature-specific research notes are
removed. This audit note is corroboration/correction only.

No canonical semantic state is changed.

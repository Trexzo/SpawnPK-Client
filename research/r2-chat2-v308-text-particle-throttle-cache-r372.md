# Chat 2 — exact-v308 text-particle throttle cache R372

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/l/u` -> `CLIENT_CLASS_000512` -> `TextParticleThrottleCache`
- proposal: `SEMPROP_B281E366E7FBBBD98BD8`
- review: `SEMREVIEW_ACD84A5A7EF3E4B0ECF5`

## Exact ownership

R362 already fixes `rs/l/t` as `TextParticleMarkup`.

The only exact-v308 class containing a type reference to `rs/l/u` is that owner. During
static initialization it creates one `rs/l/u(64, 0.75f, true)` and stores it behind the
`Map<Long,Long>` interface.

## Exact cache behavior

`rs/l/u` extends `LinkedHashMap<Long,Long>` and overrides only
`removeEldestEntry`.

The eldest entry is removed when:

`size() > 512`

The map is constructed access-ordered.

## Exact throttle semantics

Before TextParticleMarkup generates output, it derives one long key from:

- `text.hashCode()`
- x
- y

using repeated `key = key * 31 + component` composition.

The map value is the monotonic current time in milliseconds
(`System.nanoTime()/1_000_000`).

If a matching key exists and is younger than **50 ms**, TextParticleMarkup returns its
empty output immediately. Otherwise it stores the new timestamp and continues generation.

## Withheld neighbors

- `rs/l/x` + `rs/l/x$a` form a readable align-markup parser, but no other exact-v308
  class references them; they remain withheld as isolated/dead behavior.
- `rs/l/p`, `rs/l/r`, `rs/l/w`, and `rs/l/z` are empty compiler-generated
  constructor-token classes used only as null discriminator parameters for already-reviewed
  nested spec classes. They retain no independent semantic identity.

R372 is non-canonical semantic research only.

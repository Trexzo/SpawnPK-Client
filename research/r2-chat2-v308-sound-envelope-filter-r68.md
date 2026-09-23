# Chat 2 — exact-v308 sound envelope / filter semantics R68

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R68 is a separate non-canonical class-only semantic review batch extending the recovered
audio stack around R67 `MidiPlayer`.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_3C6B16405A7D17754AA5`
- field/method proposals: **0**

## Stable-ID verification

Core's exact `seed_lineage()` ordering over the complete `rs/` baseline gives:

- `rs/w/a` -> `CLIENT_CLASS_001109`
- `rs/w/b` -> `CLIENT_CLASS_001110`

## `rs/w/a` -> `SoundEnvelope`

The class decodes:

- one waveform/form byte;
- two start/end integers;
- a variable number of segment durations;
- a parallel variable number of segment amplitude/phase values.

Its reset method clears segment cursor, interpolation step, current amplitude and elapsed
sample state.

Its sampler accepts a total sample count and advances through segment boundaries while
linearly interpolating the current value. The returned value is the current envelope
amplitude after fixed-point interpolation.

R68 `SoundFilter` consumes this exact class while decoding filter modulation data.

## `rs/w/b` -> `SoundFilter`

The class owns two filter banks. Each bank can contain up to four pole pairs and has
per-stage start/end frequency and attenuation parameters.

Its coefficient generator:

1. interpolates global gain for bank 0;
2. interpolates stage attenuation;
3. converts encoded pitch into angular frequency;
4. constructs second-order coefficients using cosine and squared attenuation;
5. recursively folds later stages into the earlier coefficients;
6. exports the resulting coefficients as fixed-point integers.

The decoder reads:

- packed stage counts for the two banks;
- start/end global gain;
- per-stage frequency and attenuation data;
- alternate endpoint values selected by a bit mask;
- an optional `SoundEnvelope` when those endpoints differ.

That is an exact audio-filter/coefficient-generation contract, so `SoundFilter` is the
conservative semantic name.

## Naming boundary

Both names are semantic recovery names. R68 does not claim they are verbatim original
SpawnPK developer identifiers.

## Acceptance boundary

Chat 2 does not promote R68. Main/Core may accept either proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_3C6B16405A7D17754AA5`.

# Chat 2 — exact-v308 instrument / sound effect semantics R69

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R69 is a separate non-canonical class-only semantic review batch completing the compact
synthesized-sound stack started by R68.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_6ED5FDFC81606A4F1D6C`
- field/method proposals: **0**

## Stable-ID verification

Core's exact `seed_lineage()` ordering over the complete `rs/` baseline gives:

- `rs/w/d` -> `CLIENT_CLASS_001112`
- `rs/w/e` -> `CLIENT_CLASS_001113`

## `rs/w/d` -> `Instrument`

This class is one complete synthesized sound voice.

It owns several R68 `SoundEnvelope` instances for base pitch/volume and optional
pitch-modulation, amplitude-modulation and gating pairs. It also owns five oscillator
voice parameter slots, delay/feedback state, one R68 `SoundFilter`, and the filter's
modulation envelope.

The synthesis path renders into a shared integer PCM buffer. It:

1. resets and samples the pitch/volume envelopes;
2. applies optional pitch and volume modulation;
3. accumulates up to five delayed oscillator voices;
4. applies optional gating;
5. applies echo/delay feedback;
6. runs the R68 SoundFilter;
7. clamps the final samples to the signed 16-bit range.

The decoder reads exactly the parameters needed by that graph from R29 `Stream`.

That contract is a synthesized `Instrument`.

## `rs/w/e` -> `SoundEffect`

This class owns up to ten Instruments plus loop/start/end timing.

Its mixer converts instrument duration and offset values into 22050-Hz sample positions,
asks each Instrument to synthesize its sample block, and mixes those blocks into one
shared PCM byte buffer.

Its output method writes a real RIFF/WAVE header:

- `RIFF`
- `WAVE`
- `fmt `
- mono PCM
- 22050 Hz
- 8-bit samples
- `data` chunk length

and then returns the Stream containing the complete WAV payload.

The static archive loader reads sound-effect ids until the 65535 sentinel, decodes each
SoundEffect, stores it in a registry and records its normalized start offset.

That fixes the semantic identity as `SoundEffect`.

## Naming boundary

Both names are semantic recovery names. R69 does not claim they are verbatim original
SpawnPK developer identifiers.

## Acceptance boundary

Chat 2 does not promote R69. Main/Core may accept either proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_6ED5FDFC81606A4F1D6C`.

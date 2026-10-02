# Chat 2 — exact-v308 audio synthesis and MIDI subsystem R373

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/w/a` -> `CLIENT_CLASS_001109` -> `AudioEnvelope`
- `rs/w/b` -> `CLIENT_CLASS_001110` -> `AudioFilter`
- `rs/w/c` -> `CLIENT_CLASS_001111` -> `MidiPlayer`
- `rs/w/d` -> `CLIENT_CLASS_001112` -> `SoundInstrument`
- `rs/w/e` -> `CLIENT_CLASS_001113` -> `SoundEffect`
- review: `SEMREVIEW_768AD561B49679569DE5`

## PCM synthesis stack

`AudioEnvelope` decodes form/start/end plus breakpoint arrays and exposes a resettable per-sample interpolation step.

`AudioFilter` decodes paired filter stages and computes interpolated coefficient tables from its stored frequency/gain parameters.

`SoundInstrument` owns the pitch/volume/modulation envelopes, oscillator/delay state and one filter. Its main synthesis method generates the integer PCM sample buffer and applies the filter.

`SoundEffect` owns up to ten SoundInstrument records, mixes their generated samples, tracks effect timing and exposes the mixed result through Stream.

## MIDI path

`MidiPlayer` is separate from the PCM synthesis stack. It owns Java MIDI Sequence/Sequencer/Synthesizer state, loads sequences, starts/stops playback and controls volume through channel controller 7 / compatible mixer gain. Exact-v308 consumers include Client and the runtime/signlink helper.

## Stable identity

The stable IDs follow the exact one-based lexicographic v308 JAR lineage and sit immediately before the already-observed rs/y and rs/z families.

R373 is non-canonical semantic research only.

# Chat 2 — exact-v308 SoundPlayer R429

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/L` -> `CLIENT_CLASS_000039` -> `SoundPlayer`
- proposal: `SEMPROP_66751912BB45CEC29C6A`
- review: `SEMREVIEW_2FA18C288B46381C3B30`

## Exact playback role

`rs/L` implements `Runnable`.

Its live constructor receives:

- an `InputStream`;
- per-sound volume/intensity;
- a playback delay.

Unless the global sound level is disabled, construction starts a dedicated thread.

The run path:

1. obtains an `AudioInputStream` from the configured stream/byte source;
2. converts it to PCM_SIGNED, 16-bit audio;
3. opens a Java Sound `Clip`;
4. applies master gain;
5. sleeps the requested delay;
6. starts the clip;
7. monitors playback/global gain changes;
8. flushes/closes the clip and closes the audio stream.

## Volume state

The gain path uses `FloatControl.Type.MASTER_GAIN`.

It combines the per-sound level with the class-global sound setting, clamps the linear
amplitude and converts it to decibels with `20 * log10(amplitude)`.

The class also owns the global sound-level setter. Exact v308 emits:

- `::soundoff` when the setting reaches 4;
- `::soundon` otherwise.

## Exact ownership

`Client` is the only external exact-v308 class with a direct `rs/L` type reference.

Music/MIDI remains separately owned by the recovered MidiPlayer subsystem, so R429 does not
broaden this class into a generic audio manager.

## Historical corroboration

Several historical RSPS clients preserve a custom class named `SoundPlayer` implementing
`Runnable` around `AudioInputStream`, Java Sound `Clip` and master-gain control. That
source family is corroborative only; exact-v308 bytecode remains primary authority.

R429 remains non-canonical Chat 2 semantic research only.

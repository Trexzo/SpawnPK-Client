# Chat 2 — SoundPlayer R375

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/L` -> `CLIENT_CLASS_000039` -> `SoundPlayer`
- proposal: `SEMPROP_66751912BB45CEC29C6A`
- review: `SEMREVIEW_1A1101F8E421545B3AE0`

## Exact-v308 behavior

`rs/L`:

- implements `Runnable`;
- accepts `InputStream, soundLevel, delay`;
- launches a background thread;
- reads JavaSound audio through `AudioSystem`;
- normalizes to 16-bit PCM_SIGNED;
- opens a `Clip`;
- drives `MASTER_GAIN`;
- delays playback when requested;
- tracks runtime volume and supports `::soundon` / `::soundoff`;
- can reuse cached sound bytes.

Client is the only external exact-v308 class referencing it and constructs it from the
queued sound-effect path.

## Historical source lineage

Public 317/Elvarg-derived clients preserve a custom class named `SoundPlayer` with the same
core identity:

- `Runnable`;
- `InputStream,int,int` constructor;
- background thread;
- `AudioInputStream`;
- `Clip`;
- `MASTER_GAIN`;
- sound level + delay.

v308 has evolved the implementation, so R375 treats this as source-lineage recovery rather
than a byte-for-byte historical-source claim.

## Boundary

R375 remains non-canonical semantic research only.

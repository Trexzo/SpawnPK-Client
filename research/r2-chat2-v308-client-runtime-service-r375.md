# Chat 2 — exact-v308 client runtime service R375

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/v/a` -> `CLIENT_CLASS_001106` -> `ClientRuntimeService`
- proposal: `SEMPROP_16F4F934494F2A3E57EB`
- review: `SEMREVIEW_9F01212DAF9DD24D8C19`

## Runtime service

The class is initialized with the client host InetAddress and starts its own daemon service thread.

Its request loop handles several legacy client infrastructure responsibilities:

- socket creation;
- daemon Runnable/thread startup with priority;
- DNS/host lookup;
- URL/code-base DataInputStream creation;
- queued file/audio work;
- MIDI handoff through the live R373 MidiPlayer.

## Cache ownership

The service opens and retains the main cache RandomAccessFile plus five cache index RandomAccessFiles under the selected client data/cache directory.

## Naming boundary

This role closely resembles the historical RuneScape client Signlink service, but R375 intentionally uses the descriptive name `ClientRuntimeService` rather than claiming a lost original identifier.

The nested `rs/v/a$a` enum exposes LEFT/RIGHT/NORMAL but its precise feature meaning is not established strongly enough to name.

R375 remains non-canonical semantic research only.

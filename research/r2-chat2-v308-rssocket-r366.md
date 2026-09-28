# Chat 2 — exact-v308 RSSocket R366

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/q/b` -> `CLIENT_CLASS_000763` -> `RSSocket`
- proposal: `SEMPROP_FCC1E332B866BE5426B5`
- review: `SEMREVIEW_E07DC3208D8F6F9D01B2`

## Exact connection role

Client constructs this class directly from its live game `Socket` during connection/login
setup.

The class owns:

- the Socket;
- InputStream;
- OutputStream;
- an async circular write buffer;
- writer/read cursors;
- writer-thread state;
- close/error state.

It performs direct reads while queued writes are flushed from its Runnable writer thread.

## Legacy source fingerprint

Exact v308 retains distinctive 317-client strings and control flow:

- `Error closing stream`
- `Error in writer thread`
- `EOF`
- circular-buffer overflow protection
- lazy writer-thread startup
- Runnable output flushing.

Public 317 client source identifies this exact class family as `RSSocket`.

## Boundary

This is the game connection wrapper itself, not a packet codec or higher-level session
manager.

R366 remains non-canonical semantic research only.

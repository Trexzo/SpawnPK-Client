# Chat 2 — source-proven Censor R373

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/d/c` -> `CLIENT_CLASS_000112` -> `Censor`
- proposal: `SEMPROP_D1E91044A982113CAA1D`
- review: `SEMREVIEW_49EB6237A9C765E8B723`

## Exact wordenc authority

The class loads:

- `fragmentsenc.txt`
- `badenc.txt`
- `domainenc.txt`
- `tldlist.txt`

from the exact-v308 archive abstraction.

Its state and methods implement the classic Jagex word-filter pipeline:

- bad-word tables plus permitted surrounding byte pairs;
- domain and TLD detection;
- fragment-table lookup;
- character normalization and symbol handling;
- leetspeak-equivalent matching;
- exception/allowed-word restoration;
- case restoration/collapse.

## Exact Client usage

Client calls the wordenc initializer during startup.

The filtered-string path is then invoked on multiple live decoded/displayed chat-message
paths before message text is published into chat/player presentation state.

## Historical identity

Historical 317/Jagex client source uses the class name `Censor` for the same four resource
files and matching filtering architecture.

The historical source supplies the semantic identifier only; exact v308 remains runtime
authority.

R373 remains non-canonical semantic research only.

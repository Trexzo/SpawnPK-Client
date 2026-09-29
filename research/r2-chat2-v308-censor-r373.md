# Chat 2 — R373 duplicate Censor audit

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

R373 retains **no semantic proposal**.

A later exact-v308/source-comparison pass independently rediscovered:

- `rs/d/c`
- `CLIENT_CLASS_000112`
- `Censor`

but this exact class identity had already been recovered in R57.

Authoritative prior ownership:

- `rs/d/c` -> `CLIENT_CLASS_000112` -> `Censor`
- proposal: `SEMPROP_D1E91044A982113CAA1D`
- review: `SEMREVIEW_49EB6237A9C765E8B723`

## New corroboration

The later pass independently reconfirmed the same exact word-filter authority:

- `fragmentsenc.txt`
- `badenc.txt`
- `domainenc.txt`
- `tldlist.txt`
- bad-word/domain/TLD/fragment lookup tables;
- normalization and leetspeak-equivalent matching;
- exact Client startup initialization and live chat filtering;
- historical 317/Jagex source identity `Censor`.

This strengthens R57 but does not create a second semantic identity.

## Boundary

The duplicate R373 candidate/review/test artifacts were removed.

R373 is a correction/corroboration note only and remains non-canonical.

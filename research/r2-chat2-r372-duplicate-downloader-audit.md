# Chat 2 — R372 duplicate downloader audit

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

R372 retains **no semantic proposal**.

Direct exact-v308 reinspection of:

- `rs/cache/a/b`
- `rs/cache/a/a`

reconfirmed the updater download architecture, but both classes were already reviewed in R23.

Authoritative prior ownership:

- `rs/cache/a/b` -> `CLIENT_CLASS_000084` -> `FileDownloader`
- `rs/cache/a/a` -> `CLIENT_CLASS_000083` -> `ClientProgressFileDownloader`

R23 review:

`SEMREVIEW_A7557C36D92989848D7C`

## New corroboration

The new exact-bytecode pass independently reconfirmed:

- the abstract URL-to-File transfer loop uses 16 KiB chunks;
- content length is read through HttpURLConnection;
- downloaded bytes and start time are retained for progress reporting;
- the abstract progress hook runs after every successful chunk;
- the Client-aware subclass formats percentage plus kb/s or mb/s throughput;
- exact callers label downloads as:
  - `Downloading main game assets..`
  - `Downloading client..`
  - `Downloading game configs..`
  - `Downloading sprites..`

This strengthens R23 but does not create a second semantic identity.

## Boundary

The temporary R372 candidate/review/test artifacts were removed.

R372 is a correction/corroboration note only and remains non-canonical.

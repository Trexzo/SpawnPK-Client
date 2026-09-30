# Chat 2 — updater URL file downloaders R406

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/cache/a/a` -> `CLIENT_CLASS_000083` -> `ClientProgressFileDownloader`
- `rs/cache/a/b` -> `CLIENT_CLASS_000084` -> `UrlFileDownloader`
- review: `SEMREVIEW_930A5A90CD3CFA2E1090`

## Stable lineage

The exact cache class ordering is:

- `rs/cache/a` -> `CLIENT_CLASS_000082`
- `rs/cache/a/a` -> `CLIENT_CLASS_000083`
- `rs/cache/a/b` -> `CLIENT_CLASS_000084`
- R64 `rs/cache/b` -> `CLIENT_CLASS_000085` -> `CacheStoreSet`

so the two downloader IDs are fixed by canonical lineage rather than inferred from a new
research-local numbering scheme.

## UrlFileDownloader

`rs/cache/a/b` is abstract.

It owns:

- source URL;
- destination File;
- downloaded byte count;
- transfer start timestamp;
- content length.

Its public transfer method:

1. removes an existing destination;
2. opens URL input and destination FileOutputStream;
3. obtains content length;
4. reads 16 KiB chunks;
5. writes each chunk;
6. increments downloaded-byte state;
7. invokes one abstract progress callback after every chunk;
8. periodically flushes after more than 1 MiB;
9. returns the downloaded File.

That fixes a generic URL-to-file streaming downloader role.

## ClientProgressFileDownloader

`rs/cache/a/a` extends that base and adds:

- live `Client`;
- one caller-supplied progress label;
- rate-calculation timestamp.

Its callback computes:

- integer completion percentage;
- elapsed transfer rate;
- exact `kb/s` and `mb/s` status strings;

then publishes them through `Client.b(percent, label, status)`.

Exact callers reuse the same implementation for:

- `Downloading main game assets..`
- `Downloading client..`
- `Downloading game configs..`
- `Downloading sprites..`

so the class is deliberately not named for one specific updater lane.

## Boundary

R406 remains non-canonical semantic research only.

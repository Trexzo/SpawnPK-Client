# Chat 2 — updater HTTP downloader family R372

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/cache/a/b` -> `CLIENT_CLASS_000083` -> `HttpFileDownloader`
- `rs/cache/a/a` -> `CLIENT_CLASS_000084` -> `ClientProgressFileDownloader`
- review: `SEMREVIEW_C02FE684F198DD354BA6`

## HttpFileDownloader

The abstract base stores:

- source URL;
- destination File;
- downloaded byte count;
- transfer start time;
- content length.

Its download method:

1. removes an existing destination;
2. opens the source URL;
3. obtains content length through HttpURLConnection;
4. streams 16 KiB chunks into FileOutputStream;
5. updates downloaded-byte state;
6. invokes the abstract progress hook per chunk;
7. periodically flushes;
8. returns the downloaded File.

## ClientProgressFileDownloader

The subclass adds only:

- `Client`;
- display/status label;
- timing state for progress display.

The progress hook computes:

- integer percentage;
- current progress text;
- transfer rate;
- kb/s vs mb/s display.

It then calls the client progress presenter.

Exact live callers use it for:

- `Downloading main game assets..`
- `Downloading client..`
- `Downloading game configs..`
- `Downloading sprites..`

## Boundary

The names describe exact transfer/presentation behavior only. They do not claim original
stripped developer identifiers.

R372 remains non-canonical semantic research only.

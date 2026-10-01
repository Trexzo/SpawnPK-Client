# Chat 2 — exact-v308 color/macOS utilities R82 correction

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Corrected source identities

- `rs/A/f` -> `CLIENT_CLASS_000009` -> `ColorTypeAdapter`
- `rs/A/o` -> `CLIENT_CLASS_000018` -> `OSXUtil`
- review: `SEMREVIEW_5F8AE08D745D419CDB40`

R82 previously used descriptive names `ColorGsonAdapter` and `MacOSWindowUtil`.

Later upstream-source reconciliation proves the stronger historical RuneLite identities.

### ColorTypeAdapter

Exact v308 serializes/deserializes `java.awt.Color` through Gson using `value` and
`falpha`, matching RuneLite `ColorTypeAdapter`.

### OSXUtil

Exact v308 owns Apple EAWT fullscreen/attention/focus helpers and preserves the exact
diagnostic `Enabled fullscreen on macOS`, matching RuneLite `OSXUtil`.

R82 remains non-canonical semantic research only.

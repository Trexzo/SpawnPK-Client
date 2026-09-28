# Chat 2 — interactive text regions R359

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/l/q` -> `CLIENT_CLASS_000507` -> `InteractiveTextRegionRegistry`
- `rs/l/q$a` -> `CLIENT_CLASS_000508` -> `InteractiveTextRegion`
- review: `SEMREVIEW_D9C0E264366D9FBF6451`

## Rich-text markup

R55 `RSFont` routes exact tags:

- `<link=...>` / `</link>`
- `<tool=...>` / `</tool>`

into the registry while calculating text bounds.

The registry owns two fixed 256-entry region arrays with active counters. Registered spans
retain source substring indexes and screen-space bounds.

## Runtime interaction

The registry:

- hit-tests regions against the live Client mouse coordinates;
- resolves hover regions;
- registers tooltip objects with the existing tooltip manager;
- activates click-capable regions by coordinates;
- extracts the registered substring and dispatches it through `Client.c(String)`.

Each `InteractiveTextRegion` stores:

- source String;
- substring start/end;
- x/y rectangle bounds;
- region-kind flag;
- optional tooltip object.

Tooltip-style regions materialize tooltip content from up to 240 characters of the source
span.

`rs/l/r` remains unnamed because it is only a synthetic constructor-token helper.

R359 remains non-canonical semantic research only.

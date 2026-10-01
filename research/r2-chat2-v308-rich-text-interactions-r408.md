# Chat 2 — exact-v308 rich-text interaction regions R408

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/l/q` -> `CLIENT_CLASS_000507` -> `RichTextInteractionRegistry`
- `rs/l/q$a` -> `CLIENT_CLASS_000508` -> `RichTextInteractionRegion`
- review: `SEMREVIEW_F1CE3E7965C335809AC0`

## Tag grammar

The registry recognizes:

- `<link=...>`
- `</link>`
- `<tool=...>`
- `</tool>`

The live text renderer calls this classifier while laying out rendered spans.

## Region registry

Two fixed **256-entry** region arrays are preallocated and reused.

Each region stores:

- source String;
- source substring begin/end indexes;
- left/top/right/bottom bounds;
- interaction-kind boolean;
- optional R207 `TooltipContent`.

Registration immediately hit-tests against live client mouse coordinates.

## Link behavior

The click path finds the topmost registered link region at the supplied pointer location,
extracts its registered source substring and calls `Client.c(String)`.

## Tooltip behavior

Tool regions lazily cache `TooltipContent` from their source substring (capped at 240
characters). The hover path submits that content through the recovered tooltip service/overlay
path.

## Boundary

The names describe the shared link/tooltip interaction infrastructure rather than any one
specific UI. R408 remains non-canonical semantic research only.

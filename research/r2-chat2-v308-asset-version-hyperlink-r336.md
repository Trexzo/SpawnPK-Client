# Chat 2 — exact-v308 AssetVersion hyperlink listener R336

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/cache/b/f` -> `CLIENT_CLASS_000095` -> `AssetVersionHyperlinkListener`
- proposal: `SEMPROP_44A7680D61FEC50ABC64`
- review: `SEMREVIEW_A25105B9DE6D869CE14E`

R23 already recovers `rs/cache/b/e` as `AssetVersion`.

When remote version retrieval fails, AssetVersion constructs an HTML `JEditorPane` containing
the exact SpawnPK connectivity troubleshooting text and a link to the SpawnPK forums. It creates
`rs/cache/b/f` and installs it directly as the pane's `HyperlinkListener`.

The listener reacts only to `ACTIVATED` events and opens the event URL via
`Desktop.getDesktop().browse(URI.create(...))`.

No other exact-v308 class constructs this listener.

The sibling `rs/cache/b/a` one-method interface remains unnamed because exact-v308 contains
no genuine interface consumer; apparent binary references are only the `rs/cache/b/a/*`
subpackage names.

R336 remains non-canonical semantic research only.

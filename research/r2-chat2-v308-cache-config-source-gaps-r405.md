# Chat 2 — source-proven cache/config gaps R405

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Retained proposals

- `rs/cache/b/f` -> `CLIENT_CLASS_000095` -> `BrowserHyperlinkListener`
- `rs/f/a` -> `CLIENT_CLASS_000167` -> `Configuration`
- review: `SEMREVIEW_CE03CC434B82E76F3095`

## BrowserHyperlinkListener

The recovered semantic source map identifies the class as
`rs.cache.updater.BrowserHyperlinkListener`.

Exact v308 independently proves the contract:

- implements `HyperlinkListener`;
- ignores non-ACTIVATED hyperlink events;
- on activation converts the event URL to a URI and calls
  `Desktop.getDesktop().browse(...)`;
- R23 `AssetVersion` constructs it for the HTML error/update message pane containing the
  SpawnPK forums hyperlink.

The class owns no unrelated behavior.

## Configuration

The recovered semantic source map identifies `rs/f/a` as `rs.Configuration`.

Exact v308 independently establishes a global configuration role:

- a very large static settings surface;
- direct references from more than one hundred project classes;
- consumers include Client, Launcher, definition loaders, cache updaters, rendering paths,
  overlays and interface/UI code;
- surviving literals include configuration/developer runtime terms such as
  `developer_console`.

R405 proposes only the class identity. It does not attempt to assign semantic names to the
large static field surface.

## Withheld source-map entry

`rs/cache/b/a` is source-mapped as `ProgressListener`, but exact v308 has no live
implementer or consumer reference to that interface. It remains intentionally unnamed
rather than being promoted from source-map provenance alone.

R405 is non-canonical Chat 2 semantic research only.

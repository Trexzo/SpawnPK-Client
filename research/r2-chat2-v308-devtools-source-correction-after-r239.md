# Chat 2 — Developer Tools source-identity correction after R239

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

Historical RuneLite source at `68c819924cfd6bfb4848c71f74c121109f289d5a` resolves two older descriptive labels without changing their review proposal counts:

- R4 `rs/s/c/a` / `CLIENT_CLASS_000887`: `InterfaceDeveloperToolsConfig` -> `DevToolsConfig`
- R10 `rs/s/c/c` / `CLIENT_CLASS_000889`: `DeveloperToolsPlugin` -> `DevToolsPlugin`

Exact v308 anchors the correction through the `devtools` config group, Developer Tools plugin descriptor, config/plugin pairing, client-toolbar lifecycle, `devtools_icon.png`, and developer-overlay registration.

- corrected R4 review: `SEMREVIEW_CAD36DBCFCA2573C4FD7`
- corrected R10 review: `SEMREVIEW_8ED0E0C3CD22F26B35F6`

No semantic acceptance is performed.

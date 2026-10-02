# Chat 2 — RuneLite plugin configuration UI R488

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/s/b/a` -> `CLIENT_CLASS_000861` -> `ConfigPanel`
- `rs/s/b/o` -> `CLIENT_CLASS_000875` -> `PluginListItem`
- `rs/s/b/q` -> `CLIENT_CLASS_000877` -> `PluginListPanel`
- review: `SEMREVIEW_B0264B4CDA2A2D771917`

The three exact-v308 classes form the embedded RuneLite plugin configuration UI.

`ConfigPanel` renders ConfigDescriptor metadata into Swing controls and persists values
through ConfigManager.

`PluginListItem` is one searchable/pinnable plugin row over
PluginConfigurationDescriptor.

`PluginListPanel` owns the searchable plugin list, exact `pinnedPlugins` persistence
key, PluginManager integration and Provider<ConfigPanel> navigation.

Historical RuneLite source matches these three roles and structures directly.

The adjacent bootstrap plugin `rs/s/b/g` is intentionally not named in R488; its exact
historical source identity is still being verified separately.

R488 remains non-canonical semantic research only.

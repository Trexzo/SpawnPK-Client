# Chat 2 — exact-v308 self-identifying menu/plugin descriptors R390

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/j/b/b` -> `CLIENT_CLASS_000309` -> `CustomMenuEntry`
- `rs/l/f/f` -> `CLIENT_CLASS_000487` -> `OverlayMenuEntry`
- `rs/s/b/n` -> `CLIENT_CLASS_000874` -> `PluginConfigurationDescriptor`
- review: `SEMREVIEW_A32F02B1FF9B7F11CAF4`

All three names survive verbatim in exact-v308 self-identifying `toString()` templates.

## CustomMenuEntry

Exact template:

`CustomMenuEntry(text=..., event=...)`

The class stores only:

- String text;
- R329 `ClientCallback` event.

Client and the custom-menu/overlay paths consume this exact value object.

## OverlayMenuEntry

Exact template:

`OverlayMenuEntry(menuAction=..., option=..., target=...)`

The object stores:

- integer menu action;
- option String;
- target String;
- nullable `Consumer<CustomMenuEntry>` bridge.

The overlay UI/menu presentation paths consume this object directly.

## PluginConfigurationDescriptor

Exact template:

`PluginConfigurationDescriptor(name=..., description=..., tags=..., plugin=..., config=..., configDescriptor=..., conflicts=...)`

The stored state matches that template exactly and joins:

- plugin metadata;
- plugin instance;
- R16 Config interface;
- R16/R389 configuration descriptors;
- conflict identifiers.

The plugin-configuration UI consumes this type directly.

R390 remains non-canonical semantic research only.

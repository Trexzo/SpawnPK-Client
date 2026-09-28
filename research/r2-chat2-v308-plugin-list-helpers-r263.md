# Chat 2 — exact-v308 Plugin List helper family R263

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic review result

- `rs/s/b/p` -> `CLIENT_CLASS_000876` -> `PluginListItemPopupMouseListener`
- `rs/s/b/r` -> `CLIENT_CLASS_000878` -> `PluginListPanelEventBusMultiplexer`
- `rs/s/b/s` -> `CLIENT_CLASS_000879` -> `PluginListPanelSearchDocumentListener`
- review: `SEMREVIEW_1B80D625D128E2E2276B`
- unresolved: **0**
- field/method proposals: **0**

## Exact source-parity boundary

The reviewed config-plugin package already includes `PluginListItem`,
`PluginListPanel`, `MultiplexingPluginPanel`, `PluginPanel`, and `EventBus`.

R263 recovers the three remaining live anonymous/helper classes around those exact source
objects.

### PluginListItem popup/hover adapter

`rs/s/b/p` is the anonymous MouseAdapter installed by the label-popup helper.

Its bytecode:

- translates the current screen pointer into source-component coordinates;
- shows the captured `JPopupMenu` at that exact point;
- saves the label foreground on enter;
- applies the RuneLite brand color;
- restores the saved foreground on exit.

RuneLite `PluginListItem.addLabelPopupMenu` contains the same anonymous class and control
flow.

### PluginListPanel event-bus muxer

`rs/s/b/r` extends the reviewed `MultiplexingPluginPanel`.

Its only overridden hooks are:

- add PluginPanel -> `EventBus.register(panel)`;
- remove PluginPanel -> `EventBus.unregister(panel)`.

RuneLite `PluginListPanel` constructs exactly this anonymous
`new MultiplexingPluginPanel(this) { ... }` implementation.

### Plugin-list search document listener

`rs/s/b/s` implements `DocumentListener`.

All three callbacks—insert, remove and change—call the same reviewed
`PluginListPanel` search refresh path. RuneLite's source has the same anonymous search-bar
DocumentListener calling `onSearchBarChanged()` from all three callbacks.

## Naming boundary

R263 uses descriptive source-parity names for anonymous/helper classes. It does not claim
that these descriptive Java identifiers existed in the original source.

With R262 + R263, the live `rs/s/b` helper surface is recovered except for classes already
reviewed independently; no compiler switch-map or dead artifact is promoted here.

## Acceptance boundary

R263 remains class-only and non-canonical. Chat 2 performs no semantic acceptance.

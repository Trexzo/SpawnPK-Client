# Chat 2 — source-proven concrete plugin layer R414

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R414 recovers twenty source-mapped concrete plugins. Every exact-v308 class directly extends
R411 `Plugin`.

Recovered plugins:

CombatInfoPlugin, ConfigPlugin, DevToolsPlugin, EntityHiderPlugin, GpuPlugin,
GroundMarkersPlugin, ItemIdSearchPlugin, InfoBoxPlugin, InteractHighlightPlugin,
KeyRemappingPlugin, LoadoutsPlugin, MenuEntrySwapperPlugin, NotesPlugin,
NotificationsPlugin, NpcIndicatorsPlugin, PlayerOutlinePlugin, PvpTrackerPlugin,
TileIndicatorsPlugin, HoverDescriptionsPlugin and TradingPostPlugin.

Review: `SEMREVIEW_EDCC8995F6CEADB35060`.

R414 uses source identity plus exact inheritance/framework joins only. It does not infer
plugin-specific gameplay policy beyond those identities.

R414 remains non-canonical semantic research only.

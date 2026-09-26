# Chat 2 — exact-v308 client sidebar and PvP Tracker sidebar R145

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R145 resolves the live client-side tab container and its distinct PvP Tracker sidebar page.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_CEECF5480BE96957E887`
- field/method proposals: **0**

## Stable IDs

- `rs/gui/J` -> `CLIENT_CLASS_000193` -> `ClientSidebarPanel`
- `rs/gui/c/a` -> `CLIENT_CLASS_000260` -> `PvPTrackerSidebarPanel`

## ClientSidebarPanel

Launcher constructs `rs/gui/J` next to the main `rs/Client` canvas.

The exact main-window flow:

- adds the client canvas to the central game container;
- adds `rs/gui/J` alongside it when the editor mode does not replace that surface;
- exposes the exact menu action `Hide/show side panel`;
- calls `setVisible(false)` on this exact component when the configured side panel is off.

The class itself extends `JPanel`, owns one `JTabbedPane`, and installs the exact live tabs:

- `Loadouts`;
- `PvP Tracker`;
- `GPU (Beta)`;
- `Development` when developer tools are enabled;
- otherwise `Item Search`.

Its child graph includes the reviewed `LoadoutFolderPanel`, the PvP Tracker page below and
the GPU/developer/item-search surfaces. Dedicated accessors expose the tabbed pane and those
child panels.

That combination fixes the role as the client's optional sidebar container rather than a
feature-specific interface.

## PvPTrackerSidebarPanel

`ClientSidebarPanel` inserts `rs/gui/c/a` under exact tab title:

`PvP Tracker`

The page itself preserves:

- `Type ::pvptracker to view overlay in-game`;
- `Most Recent 1v1 Fight`;
- `Correct overheads:`;
- `Spell casts:`;
- paired fighter rows/icons;
- explicit death-state handling.

Two public update methods enqueue `EventQueue.invokeLater` runnables for the mirrored
fighter sides. Those runnables update name/death state and the packet-provided tracker metric
strings without touching an unrelated subsystem.

This is distinct from R12 `PvPTrackerPanel` (`rs/s/q/b`), which is the plugin side panel
with exact `Current Fight`, fight-history filtering and plugin-navigation behavior.

The `SidebarPanel` suffix therefore records a real exact-v308 architectural distinction,
not a naming synonym.

## Acceptance boundary

Chat 2 does not promote R145. Main/Core may accept either proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_CEECF5480BE96957E887`.

# Chat 2 — exact-v308 navigation orchestration R149

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R149 resolves the two remaining high-value orchestration classes around the reviewed
NavigationButton / ClientUI / PluginPanel graph.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_CF423B0AACFCEC690C03`
- field/method proposals: **0**

## Stable IDs

- `rs/ui/e` -> `CLIENT_CLASS_001095` -> `ClientToolbar`
- `rs/ui/k` -> `CLIENT_CLASS_001101` -> `MultiplexingPluginPanel`

R19 already recovered `rs/ui/l$a` as `NavigationButtonBuilder`, so R149 deliberately
does not duplicate that class.

## ClientToolbar

`rs/ui/e` owns:

- an EventBus;
- a Set of R12 `NavigationButton` values.

Registration is idempotent. When a new button is added, the manager posts exact:

`NavigationButtonAdded`

with that same button.

When a registered button is removed, it posts exact:

`NavigationButtonRemoved`.

R147 `ClientUI` consumes these two events to:

- add/remove toolbar/title-toolbar buttons;
- add/remove associated R148 `PluginPanel` content.

That fixes this class as the NavigationButton registration/event manager.

RuneLite `96036d17d0f14f2bd20fb174054fe6f46570b613` contains `net.runelite.client.ui.ClientToolbar` with the same EventBus, Set<NavigationButton>, idempotent registration, conditional removal and exact NavigationButtonAdded/NavigationButtonRemoved event posting. The descriptive `NavigationButtonManager` label is therefore corrected to the historical source name `ClientToolbar`.

## MultiplexingPluginPanel

`rs/ui/k` extends R148 `PluginPanel` and uses a `CardLayout`.

It owns:

- an active/inactive flag;
- the current `PluginPanel`;
- a stack represented by its child-component order.

Selecting a panel:

- deactivates the previous panel and activates the new one when the stack is live;
- pushes a new panel when absent;
- if the panel already exists deeper in the stack, removes every panel above it;
- shows the selected panel by an identity-hash card key.

Popping:

- reveals the previous panel;
- removes the former top panel;
- preserves the root panel.

The exact assertion is:

`Cannot pop last component`

Its own activate/deactivate hooks forward directly to the current child panel.

RuneLite source at `6610375cca74469040ebcf03613866f6b3360668` contains `net.runelite.client.ui.MultiplexingPluginPanel` with the same `PluginPanel(false)` constructor, `CardLayout`, active/current state, identity-hash card keys, push/pop behavior, lifecycle forwarding and exact `Cannot pop last component` assertion. This upgrades the earlier descriptive `PluginPanelStack` label to recovered source identity.

## Acceptance boundary

Chat 2 does not promote R149. Main/Core may accept either proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_410CFE5335C7F4D7D4F0`.

## R233 correction note

The earlier R149 proposal `SEMPROP_089A22046632B2B2A74D` / review `SEMREVIEW_410CFE5335C7F4D7D4F0` used the descriptive name `PluginPanelStack`. The source match above supersedes it with proposal `SEMPROP_BCB1A62D0D24D1D49A52` and corrected review `SEMREVIEW_6E440D0AAE56E0CE650B`. Proposal count remains unchanged.

## R233 paired toolbar correction

The old `NavigationButtonManager` proposal `SEMPROP_BF68A433F3A262F89B68` is superseded by `SEMPROP_F5250D0BCC1BBBB5A604` (`ClientToolbar`). Corrected R149 review: `SEMREVIEW_CF423B0AACFCEC690C03`. This correction is atomic with R148's `ClientToolbar` -> `ClientPluginToolbar` rename, preventing any duplicate semantic name state.

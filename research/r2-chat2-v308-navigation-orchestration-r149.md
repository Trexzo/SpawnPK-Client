# Chat 2 — exact-v308 navigation orchestration R149

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R149 resolves the two remaining high-value orchestration classes around the reviewed
NavigationButton / ClientUI / PluginPanel graph.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_410CFE5335C7F4D7D4F0`
- field/method proposals: **0**

## Stable IDs

- `rs/ui/e` -> `CLIENT_CLASS_001095` -> `NavigationButtonManager`
- `rs/ui/k` -> `CLIENT_CLASS_001101` -> `PluginPanelStack`

R19 already recovered `rs/ui/l$a` as `NavigationButtonBuilder`, so R149 deliberately
does not duplicate that class.

## NavigationButtonManager

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

## PluginPanelStack

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

## Acceptance boundary

Chat 2 does not promote R149. Main/Core may accept either proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_410CFE5335C7F4D7D4F0`.

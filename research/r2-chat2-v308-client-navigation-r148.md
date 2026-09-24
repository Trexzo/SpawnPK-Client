# Chat 2 — exact-v308 ClientUI navigation shell R148

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R148 resolves the four core presentation/navigation primitives directly owned by R147
`ClientUI`.

## Deterministic review result

- candidate classes: **4**
- resolved proposals: **4**
- unresolved: **0**
- review ID: `SEMREVIEW_904385EDA852ACED380C`
- field/method proposals: **0**

## Stable IDs

- `rs/ui/a` -> `CLIENT_CLASS_001016` -> `ClientPanel`
- `rs/ui/b` -> `CLIENT_CLASS_001027` -> `ClientToolbar`
- `rs/ui/c` -> `CLIENT_CLASS_001032` -> `ClientTitleToolbar`
- `rs/ui/m` -> `CLIENT_CLASS_001104` -> `PluginPanel`

## ClientPanel

The final JPanel receives the live game Applet/Client and adds it at
`BorderLayout.CENTER`.

It fixes size/minimum/preferred size to:

`765 x 503`

and uses a black background.

R147 `ClientUI` constructs this exact panel around its live `rs/Client` before inserting
it into the main window.

## ClientToolbar

`rs/ui/b` extends vertical `JToolBar`.

Exact base dimensions are:

`36 x 503`

It is non-floatable and stores a sorted:

`Map<NavigationButton, Component>`

Add/remove operations rebuild the visible toolbar. Buttons are ordered by their section
flag, priority and title, with glue/separator between the two groups.

R147 `ClientUI` routes ordinary `NavigationButtonAdded` events into this toolbar.

## ClientTitleToolbar

`rs/ui/c` is the companion NavigationButton container placed directly into the custom
window title pane as a trailing component.

It also stores a sorted:

`Map<NavigationButton, Component>`

R147 `ClientUI` sends title-area navigation buttons here instead of to ClientToolbar.

Ordering uses NavigationButton priority and title.

## PluginPanel

`rs/ui/m` is the shared plugin-side-panel base.

Its default layout provides:

- a 350/367px width model;
- border/background setup;
- scroll pane;
- inner content JPanel.

R12 `NavigationButton` optionally owns one `PluginPanel`.

When a navigation button is registered, R147 `ClientUI` installs that panel into its
CardLayout. When selected/deselected, ClientUI invokes the panel's paired lifecycle hooks
`J_()` and `K_()`.

That fixes the class as the common plugin panel base rather than an arbitrary Swing panel.

## Acceptance boundary

Chat 2 does not promote R148. Main/Core may accept any subset only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_904385EDA852ACED380C`.

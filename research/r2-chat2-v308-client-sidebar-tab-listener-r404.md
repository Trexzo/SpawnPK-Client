# Chat 2 — client sidebar tab listener R404

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

- `rs/gui/L` -> `CLIENT_CLASS_000195` -> `ClientSidebarTabChangeListener`
- review: `SEMREVIEW_51523639FA40BCB1E765`

R145 `ClientSidebarPanel` constructs this listener and installs it directly on its
`JTabbedPane`.

On each ChangeEvent it reads the selected tab index and triggers the Launcher refresh/update
path. It has no second event role.

Sibling `rs/gui/K` remains unnamed because its mouseEntered/mouseExited implementation is
effectively no-op in exact v308.

R404 remains non-canonical semantic research only.

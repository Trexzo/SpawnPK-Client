# Chat 2 — Client sidebar tab listener R372

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

- `rs/gui/L` -> `CLIENT_CLASS_000195` -> `ClientSidebarTabChangeListener`
- proposal: `SEMPROP_6CC0B81B2E3B79F8DBE5`
- review: `SEMREVIEW_76A9F6B4787D50C7C7E9`

R145 already fixes `rs/gui/J` as `ClientSidebarPanel`. It creates exactly one
`rs/gui/L` and installs it on the live sidebar JTabbedPane with addChangeListener.

The listener reads the selected tab index and invokes the live Launcher refresh/update path.
It owns no second behavior.

Nearby `rs/gui/K` remains unnamed because its mouse-enter/exit methods are effectively
no-ops in exact v308. `rs/gui/Q` remains unnamed because it is an empty shell.

R372 remains non-canonical semantic research only.

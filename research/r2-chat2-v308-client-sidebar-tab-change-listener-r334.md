# Chat 2 continuation — client sidebar tab change listener R334

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/gui/L`
- stable ID: `CLIENT_CLASS_000195`
- semantic: `ClientSidebarTabChangeListener`
- review: `SEMREVIEW_51523639FA40BCB1E765`

## Exact ownership

R145 fixes `rs/gui/J` as `ClientSidebarPanel`.

That panel creates one `rs/gui/L` and installs it on its live `JTabbedPane` through
`addChangeListener`.

## Exact behavior

`rs/gui/L` implements `ChangeListener`.

On each state change it:

1. casts the event source to `JTabbedPane`;
2. reads the selected tab index;
3. calls `Launcher.n().d()`.

No packet, mouse, keyboard or feature-specific state is owned by the listener.

## Withheld sibling

`rs/gui/K` is also constructed by ClientSidebarPanel, but its mouseEntered/mouseExited
methods are effectively no-ops in exact v308. It remains intentionally unnamed.

R334 remains non-canonical semantic research only.

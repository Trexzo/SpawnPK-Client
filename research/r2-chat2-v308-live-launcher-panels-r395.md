# Chat 2 — exact-v308 live launcher panels R395

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Corrected retained result

- `rs/gui/E` -> `CLIENT_CLASS_000188` -> `ClientViewportPanel`
- review: `SEMREVIEW_EB60905443023635BE59`

The earlier stale-branch R395 draft also repeated:

- `rs/gui/L` -> `CLIENT_CLASS_000195` -> `ClientSidebarTabChangeListener`

That proposal is removed here because **R372 already owns the exact same class/name/stable ID**.
R395 therefore retains only its unique viewport-panel recovery.

## ClientViewportPanel

Launcher constructs one `rs/gui/E`, configures it with a black background and
`BorderLayout`, and inserts the live `rs.Client` at `BorderLayout.CENTER`.

For the fixed shell it is explicitly sized/preferred/minimum-sized to 765x503.

Launcher then places this panel in the main Swing shell beside R145
`ClientSidebarPanel`.

That fixes the role as the central live client viewport host.

## Boundary

- R372 remains authoritative for `ClientSidebarTabChangeListener`.
- `rs/gui/B`: stale timer ActionListener; current Launcher uses an invokedynamic listener.
- `rs/gui/F`: effectively empty JPanel shell.
- `rs/gui/K`: inert MouseAdapter.
- `rs/gui/Q`: empty class.

R395 remains non-canonical semantic research only.

# Chat 2 — exact-v308 game client panel R352

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/gui/E` -> `CLIENT_CLASS_000188` -> `GameClientPanel`
- proposal: `SEMPROP_B0461C7A173A9D960EF5`
- review: `SEMREVIEW_5179DE55019E9DC48390`

Launcher creates this JPanel immediately after constructing the live `Client`.

It configures the panel with:

- exact fixed game dimensions 765 x 503 in the non-dynamic path;
- preferred size 765 x 503;
- `BorderLayout`;
- black background.

Launcher then initializes/starts the Client and adds the Client component at
`BorderLayout.CENTER`.

The class has no independent behavior, so the exact containment role is the strongest and
safest semantic identity.

R352 remains non-canonical semantic research.

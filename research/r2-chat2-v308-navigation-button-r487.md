# Chat 2 — NavigationButton identities R487

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/ui/l` -> `CLIENT_CLASS_001102` -> `NavigationButton`
- `rs/ui/l$a` -> `CLIENT_CLASS_001103` -> `NavigationButtonBuilder`
- review: `SEMREVIEW_90DC1B171C6BBBAA0F0D`

Exact-v308 preserves both source-style toString identities directly. The nested builder
owns the complete fluent construction surface and builds the outer NavigationButton.

R487 remains non-canonical semantic research only.

# Chat 2 — NavigationButton builder R487

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R487 retains one genuinely new proposal:

- `rs/ui/l$a` -> `CLIENT_CLASS_001103` -> `NavigationButtonBuilder`

Review: `SEMREVIEW_E31798F94A68F4F2CC04`

The same scan independently recovered outer `rs/ui/l -> NavigationButton`, but R12
already owns that exact class and proposal `SEMPROP_B6CE6B18C0477EAC3D6E`.
The outer duplicate was removed from R487.

Exact-v308 preserves the nested source-style
`NavigationButton.NavigationButtonBuilder(...)` identity, and build() produces the R12
NavigationButton directly.

R487 remains non-canonical semantic research only.

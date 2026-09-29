# Chat 2 — exact-v308 Loadout folder controls R394

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R394 recovers the complete single-purpose folder popup/control family owned by R390
`LoadoutsPanel` and R143 `LoadoutManager`.

The popup factory preserves the exact title `Loadout folders` and actions:

- `Create new folder`
- `Rename`
- `Move up`
- `Move down`
- `Delete`

Recovered classes:

- `rs/gui/b/a/n` -> `LoadoutFolderMenuFactory`
- `o` -> `SelectLoadoutFolderAction`
- `p/q` -> open/commit create-folder actions
- `r/s` -> open/commit rename-folder actions
- `t/u` -> move-folder up/down actions
- `v/w/x` -> open/confirm/cancel delete-folder actions

The delete cancel button preserves exact text `No, Nevermind.`.

All names describe exact UI/control behavior only. R394 remains non-canonical research.

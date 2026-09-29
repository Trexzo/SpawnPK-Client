# Chat 2 — R403 duplicate custom-menu audit

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

R403 retains **no semantic proposal**.

Attempted owners were already reviewed:

- R281: `rs/j/b/a` / `CLIENT_CLASS_000308` -> `CustomMenuSubmenu`
- R12: `rs/j/b/b` / `CLIENT_CLASS_000309` -> `CustomMenuEntry`
- R281: `rs/j/b/d` / `CLIENT_CLASS_000312` -> `CustomMenuManager`

The newer pass adds corroboration: the manager keeps callback/submenu maps aligned while
inserting and swapping the Client's parallel menu arrays, uses exact default parent label
`Choose Sub-Option`, and dispatches the selected callback/submenu. The entry's exact
self-identifying `toString` remains `CustomMenuEntry(text=..., event=...)`.

R403 is correction/corroboration only. No candidate/review/test remains.

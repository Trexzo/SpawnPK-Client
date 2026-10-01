# Chat 2 R3 — Item Search sidebar panel R358

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

- `rs/gui/G` -> `CLIENT_CLASS_000190` -> `ItemSearchSidebarPanel`
- proposal: `SEMPROP_A4AD083385525613AE87`
- review: `SEMREVIEW_B4DD52506B6214D013E2`

R357 proves this class is installed as the exact `Item Search` tab in
`LauncherSidePanel` when the developer panel is unavailable.

R301 already recovered its two direct action children:

- `rs/gui/H` -> `ItemSearchEnterAction`
- `rs/gui/I` -> `ItemSearchButtonAction`

Both dispatch into G's private search routine. G owns the search field, Search button,
scrollable results and item-result presentation.

R358 closes the parent/child family and remains non-canonical semantic research only.

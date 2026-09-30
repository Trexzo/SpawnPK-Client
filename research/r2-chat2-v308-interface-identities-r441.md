# Chat 2 — exact-v308 interface identities R441

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/n/c/al` -> `CLIENT_CLASS_000613` -> `ItemLoadoutModificationInterface`
- `rs/n/c/aq` -> `CLIENT_CLASS_000621` -> `MakeQuantitySelectionInterface`
- `rs/n/c/w` -> `CLIENT_CLASS_000676` -> `TextColorSelectionInterface`
- `rs/n/c/f` -> `CLIENT_CLASS_000659` -> `AttackOptionsInterface`
- review: `SEMREVIEW_3D00639EAEBB804CB65F`

## Item Loadout Modification

Root **33000** uses exact title `Item Loadout Modification Interface`, loadout resources,
`LMS Loadout`, Save, Set as default and Reset to default controls.

This is distinct from the previously recovered Swing/loadout manager family under
`rs/gui/b/*`: this class is the in-game custom interface builder.

## Make Quantity Selection

The interface asks:

`How many would you like to make?`

It offers 1 / 5 / 10 / X / All quantities and selectable output images under the exact
instruction to choose a quantity and click an image.

## Text Color Selection

The screen's own title is `Text Color Selection Menu`. It exposes font and shadow color
selection, a color palette, Confirm colors and Cancel colors actions.

## Attack Options

The interface contains exact section headings:

- `Player attack options`
- `NPC/Bot attack options`

and the exact toggle `Always right-click clan members`.

## Boundary

All names describe exact client interface roles only. No gameplay, persistence or
server-authoritative behavior is inferred.

R441 remains non-canonical semantic research only.

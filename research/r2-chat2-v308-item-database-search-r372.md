# Chat 2 — item database search Swing helpers R372

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/gui/G` -> `CLIENT_CLASS_000190` -> `ItemDatabaseSearchPanel`
- `rs/gui/H` -> `CLIENT_CLASS_000191` -> `ItemDatabaseSearchFieldActionListener`
- `rs/gui/I` -> `CLIENT_CLASS_000192` -> `ItemDatabaseSearchButtonActionListener`
- review: `SEMREVIEW_B6361D644DD7404B6562`

## Panel

The panel owns a search field, a results text area, a scroll pane and an exact `Search`
button.

Its search routine contains the exact user-facing strings:

- `Please wait until the client has loaded the item database!`
- `Please have at least 3 letters in your search term!`

Once the item-definition table is available, it iterates item definitions, performs
case-insensitive name matching and writes matching item ids/names into the results text area.

## Listener split

`rs/gui/H` is attached to the JTextField action path, so Enter in the field invokes the
same search routine.

`rs/gui/I` is attached to the exact `Search` JButton and invokes the same routine.

Both listener classes contain only the synthetic panel owner and no independent behavior.

## Boundary

The names are exact-behavior descriptive names. They do not claim original stripped source
identifiers.

R372 remains non-canonical semantic research only.

# Chat 2 — dropdown widget family R377

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/n/a/a/a` -> `CLIENT_CLASS_000527` -> `DropdownInterface`
- `rs/n/a/a/d` -> `CLIENT_CLASS_000530` -> `DropDownOption`
- review: `SEMREVIEW_170AA2A56AE794EA5E99`

## DropdownInterface

The class directly extends the exact RSInterface type.

Its factory:

1. creates one custom widget;
2. builds a List of `rs/n/a/a/d` entries from supplied Strings;
3. initializes the visible text from the first option;
4. uses exact action/default text `Select`;
5. installs itself into the global interface table.

Its selection method resolves a clicked option index, stores that index, updates the widget
display text from the selected option and triggers the dropdown redraw path when active.

R118 already fixes ScriptPacket ID 40 as `DropdownPacketHandler` targeting this exact class.

## DropDownOption

The option class contains exactly two String fields and standard value-object equality/hash
behavior.

Most importantly, its exact `toString()` representation preserves:

`DropDownOption(text=...`

That surviving token provides direct source/domain naming authority.

## Boundary

R377 is non-canonical class-only research and performs no acceptance or source rewrite.

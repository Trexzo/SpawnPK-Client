# Chat 2 — source-proven dropdown option R407

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/n/a/a/d` -> `CLIENT_CLASS_000530` -> `DropDownOption`
- proposal: `SEMPROP_5E4E2C4B75F10C7A82A1`
- review: `SEMREVIEW_CE3DF575CB2A068F50F8`

The recovered semantic source map identifies this exact class as
`rs.interfaces.components.dropdown.DropDownOption`.

Exact v308 independently corroborates it:

- two String fields only;
- constructor/getter/setter surface;
- value-style equals/hashCode/toString;
- R283 dropdown components store lists of this exact type;
- exact interface code updates option text/description through the two String setters;
- exact packet/state code constructs options from decoded String pairs, installs the list and
  selects an option by the first String value.

R407 names only the class. The two individual String members remain outside Chat 2's current
class-only proposal boundary.

R407 is non-canonical semantic research only.

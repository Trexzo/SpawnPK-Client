# Chat 2 — exact-v308 two-option selection patch R444

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/n/c/aT` -> `CLIENT_CLASS_000595` -> `TwoOptionSelectionInterfacePatch`
- proposal: `SEMPROP_BC5B42D98933E5D9F3B4`
- review: `SEMREVIEW_09192F470EB7066E1F79`

## Stable identity

The canonical run is directly bracketed by prior reviewed owners:

- `rs/n/c/aS` -> 000594
- `rs/n/c/aT` -> 000595
- `rs/n/c/aU` -> 000596
- `rs/n/c/aV` -> 000597
- `rs/n/c/aW` -> 000598

## Exact behavior

R444 does not create an independent root. It loads existing widget **6960** and replaces its
child arrays with a six-child arrangement.

New controls:

- **30583** — visible text `1`, tooltip `Select option`
- **30584** — visible text `2`, tooltip `Select option`
- **6961** — visible text `Close Window`, tooltip `Close`

Widgets 30583 and 30584 are explicitly marked active.

The resulting root children are:

- 6961
- 6962
- 6963
- 6964
- 30583
- 30584

## Boundary

Nothing in exact v308 identifies what business/domain choices `1` and `2` mean.
The semantic name therefore describes only the exact two-option UI patch.

R444 remains non-canonical semantic research only.

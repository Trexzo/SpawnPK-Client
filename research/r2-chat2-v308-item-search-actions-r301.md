# Chat 2 — exact-v308 Item Search actions R301

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic result

- `rs/gui/H` -> `CLIENT_CLASS_000191` -> `ItemSearchEnterAction`
- `rs/gui/I` -> `CLIENT_CLASS_000192` -> `ItemSearchButtonAction`
- review: `SEMREVIEW_DA273FB80A687E997A87`
- unresolved: **0**
- member proposals: **0**

## Exact-v308 contract

R146 already owns `rs/gui/G` as `ItemSearchSidebarPanel`.

Its constructor wires two dedicated listeners to the same private search routine:

1. `rs/gui/H` is attached directly to the item-search `JTextField` with `addActionListener`. Its `actionPerformed` immediately calls the parent search routine. This fixes the role as the Enter/action trigger for the text field.
2. `rs/gui/I` is attached directly to the `JButton` whose exact visible text is **Search**. Its `actionPerformed` calls the same parent search routine, fixing the role as the button action.

Neither class owns independent search logic, state or side effects beyond dispatching the correctly-scoped UI trigger.

## Boundary

R301 is non-canonical semantic research only. No semantic acceptance, source rewrite or source materialization is performed.

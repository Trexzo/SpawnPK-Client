# Chat 2 — ConfigObject R400

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

`rs/e/j` -> `CLIENT_CLASS_000154` -> `ConfigObject`

Proposal: `SEMPROP_1659F2C7A15FDEB8F5DF`

Review: `SEMREVIEW_240C0F2942929BBFECA1`

## Exact contract

The exact-v308 interface has exactly three methods. The recovered member map fixes them as:

- `key()`
- `name()`
- `position()`

R12 `ConfigItemDescriptor` and `ConfigSectionDescriptor` both implement this interface.

RuneLite's config package exposes the same `ConfigObject` interface with the same three
methods and the same two descriptor implementations.

The older recovered source map omitted this one interface entry, so R400 relies on the exact
implementation graph plus the upstream contract instead of silently assuming package adjacency.

R400 remains non-canonical semantic research only.

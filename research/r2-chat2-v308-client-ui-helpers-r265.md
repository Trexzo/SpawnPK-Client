# Chat 2 — exact-v308 Client UI helper family R265

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic review result

- `rs/ui/d` -> `CLIENT_CLASS_001094` -> `ClientTitleToolbarLayout`
- `rs/ui/g` -> `CLIENT_CLASS_001097` -> `ClientUIExitWindowListener`
- `rs/ui/h` -> `CLIENT_CLASS_001098` -> `ClientUILayoutDelegate`
- review: `SEMREVIEW_2FC14E0A3F5079A9E46A`
- unresolved: **0**
- field/method proposals: **0**

## Exact-v308 behavior

### ClientTitleToolbarLayout

`rs/ui/d` is constructed only by reviewed `ClientTitleToolbar` and installed as its
`LayoutManager2`.

Its complete layout contract is preserved:

- preferred width = component count × 27;
- preferred height = 23;
- children start at x=4;
- child height is clamped to 23 and vertically centered;
- each child is assigned width 23;
- x advances by 23 after each child.

The proposed identifier is descriptive; the exact bytecode proves the class role, not an
original source identifier.

### ClientUIExitWindowListener

`rs/ui/g` is the `WindowAdapter` installed by reviewed `ClientUI`.

Its `windowClosing` path preserves the exact confirmation strings:

- `Are you sure you want to exit?`
- `Exit`

and the exact warning text:

- `Unexpected exception occurred while check for confirm required`

RuneLite ClientUI retains the same anonymous WindowAdapter flow: conditionally confirm, then
shut down on OK.

### ClientUILayoutDelegate

`rs/ui/h` wraps an existing `LayoutManager` and a target `JComponent`.

It delegates ordinary layout methods to the wrapped manager and, after layout, repositions the
reviewed `ClientTitleToolbar` using its preferred width and the component's current size.

Again, the proposed identifier is descriptive for an implementation helper.

## Deliberate exclusion

`rs/ui/i` is a compiler-generated enum switch map for `OSType` and remains unnamed.

## Acceptance boundary

R265 remains class-only and non-canonical. Chat 2 performs no semantic acceptance.

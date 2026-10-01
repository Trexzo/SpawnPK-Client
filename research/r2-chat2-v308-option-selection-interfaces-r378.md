# Chat 2 successor — exact-v308 option selection interfaces R378

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Hard uniqueness preflight

R373-R376 demonstrated that GitHub code search is not a safe duplicate preflight.

For R378, the complete prior-owner index was reconstructed from the repository-wide
uniqueness failure output through R372 and augmented with R377's five retained model-material
owners.

That index was intersected with exact-v308 classes carrying meaningful surviving literals.
Only two literal-rich classes remained genuinely unreviewed:

- `rs/n/c/aA`
- `rs/n/c/aT`

No other literal-rich class proceeds in this batch.

## Result

- `rs/n/c/aA` -> `CLIENT_CLASS_000576` -> `ToggleOptionSelectionInterface`
- `rs/n/c/aT` -> `CLIENT_CLASS_000595` -> `DualOptionSelectionInterface`
- review: `SEMREVIEW_B5CFE0CA554AD6C30195`

The stable IDs were cross-checked against the full exact-v308 class-entry ordering including
nested classes. Known anchors reproduce exactly:

- `rs/n/c/aC`: entry index 577 -> R2 stable id `CLIENT_CLASS_000578`
- `rs/n/c/x`: entry index 676 -> R319 stable id `CLIENT_CLASS_000677`

The same exact mapping yields:

- `rs/n/c/aA`: index 575 -> `CLIENT_CLASS_000576`
- `rs/n/c/aT`: index 594 -> `CLIENT_CLASS_000595`

## ToggleOptionSelectionInterface

`rs/n/c/aA` has no fields and only its constructor plus builder method.

The builder owns exact roots:

- 53500
- 53519

It creates the same eighteen child option widgets:

- 53501 .. 53518
- visible labels: 1 .. 18
- action: `Select option`
- invokedynamic tooltip recipe: `Selecting this option Toggle N`

The eighteen children are positioned in two distinct fixed layouts under the two roots.

No surviving resource path or feature-specific title identifies what the toggles configure.
The proposed name therefore stops at the exact selectable-toggle behavior.

## DualOptionSelectionInterface

`rs/n/c/aT` obtains existing root 6960 and replaces its child-layout arrays with six
children. The final two children are newly created:

- 30583 -> label `1`, action `Select option`
- 30584 -> label `2`, action `Select option`

Both are explicitly interactive.

It also creates:

- 6961 -> `Close Window`, action `Close`

The class is adjacent in the central interface registry to R5 TaskScrollInterface and R6
TeleportSelectionInterface, but adjacency is not semantic authority. Direct bytecode
comparison shows it does not share the teleport roots or `teleport/SPRITE` resources.

The feature noun behind root 6960 remains unresolved; the proposed name describes only the
exact two-option selection behavior.

## Boundary

Both names are descriptive exact-v308 identities only. They do not claim original stripped
developer names.

R378 remains non-canonical semantic research only.

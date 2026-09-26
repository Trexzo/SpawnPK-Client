# Chat 2 — exact-v308 RuneLite material tabs source recovery R230

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R230 recovers the two real source classes in the exact-v308 material-tabs package.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_5789FBA171B6FB2F21B5`
- field/method proposals: **0**

## Stable IDs

- `rs/ui/components/b/a` -> `CLIENT_CLASS_001060` -> `MaterialTab`
- `rs/ui/components/b/e` -> `CLIENT_CLASS_001064` -> `MaterialTabGroup`

## Source provenance

RuneLite upstream `6e74752caa80fe9cb96cd9b37207e171fa525f07` contains
`net.runelite.client.ui.components.materialtabs.MaterialTab` and
`MaterialTabGroup` with exact state and control flow preserved by v308.

`MaterialTab` retains:

- JLabel inheritance;
- selected/unselected borders;
- content JComponent;
- BooleanSupplier selection veto;
- selected flag;
- String and ImageIcon constructors;
- group-select and hover listeners;
- select/unselect behavior.

`MaterialTabGroup` retains:

- display JPanel;
- List<MaterialTab>;
- display/no-arg constructors;
- FlowLayout setup;
- indexed lookup;
- add-tab;
- select-tab with display replacement, revalidate/repaint and unselect-other-tabs.

## Compiler-artifact boundary

`rs/ui/components/b/b`, `b/c` and `b/d` are anonymous MouseAdapter helpers emitted
from MaterialTab constructors. R230 leaves them unnamed rather than promoting compiler
artifacts as source-level classes.

## Acceptance boundary

Chat 2 does not promote R230. Main/Core may accept either proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_5789FBA171B6FB2F21B5`.

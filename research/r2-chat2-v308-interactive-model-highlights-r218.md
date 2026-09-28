# Chat 2 — exact-v308 interactive model highlights R218

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R218 is a separate non-canonical class-only review for the model-derived polygon highlight
record and its client-global registry. It does not alter Main/Core's accepted semantic
authority or any prior Chat 2 review batch.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_DB704E01C67994C03183`
- field/method proposals: **0**

## Stable IDs

- `rs/l/e/j` -> `CLIENT_CLASS_000431` -> `InteractiveModelHighlight`
- `rs/l/e/k` -> `CLIENT_CLASS_000432` -> `InteractiveModelHighlightRegistry`

## `rs/l/e/j` -> `InteractiveModelHighlight`

The record contains exactly the state needed for one model-derived interactive highlight:

- one projected `java.awt.Polygon`;
- the backing target `Object`;
- normal and active/hover outline colors;
- normal and active/hover fill colors;
- one interaction/picking integer;
- one boolean active/hover flag.

The polygon is not arbitrary UI geometry. Exact producers obtain it from the v308 `Model`
polygon-projection path.

Two independently recovered consumers construct the same record family:

1. the R30 `Renderable` path creates one around a live NPC model with purple/magenta
   presentation; and
2. the R107 `EditorNpcEntity` / `EditorPlayerEntity` paths create one around editor entity
   models with green/black presentation.

The exact `Model` render/picking path then retrieves the record by interaction id, clears the
active flag, tests `Polygon.contains(mouseX, mouseY)` and sets the flag when the polygon is
hit. The stored interaction id can replace the ordinary model-picking id in that same path.

The shared client polygon renderer iterates these records and draws each polygon with the
record's state-dependent outline/fill colors. The Editor Kit paths also branch on the same
active flag to drive selection/deletion interaction.

That complete producer -> mouse-hit-test -> state-change -> draw/interaction loop fixes the
role as an interactive model highlight rather than a generic polygon DTO.

## `rs/l/e/k` -> `InteractiveModelHighlightRegistry`

`Client` constructs one global instance of this class.

The instance owns three int-keyed Trove maps of `rs/l/e/j` records. The primary live map is
populated by both normal `Renderable` and Editor Kit model-polygon producers. Scene traversal
clears the live maps before rebuilding scene presentation, `Model` looks records up by the
same interaction id used by picking, and the shared renderer consumes the primary map.

Exact v308 also retains:

- two auxiliary `rs/l/e/j` maps with much weaker live producer evidence; and
- one static integer-id set initialized from a fixed id table.

Those retained structures do not justify a narrower feature/product noun. `Registry` describes
the proven role without inventing semantics for the dormant/weakly connected state.

## R218 frontier boundary

R218 deliberately continues to withhold `rs/l/e/l` and `rs/l/e/m`.

Their behavior is mechanically clear:

- `rs/l/e/l` stores one String plus initial screen coordinates `522,330`;
- `rs/l/e/m` queues those records, moves the active text one pixel left per update and draws
  it in white until it leaves the screen.

However, the exact v308 incoming-reference surface contains no surviving direct producer for
`rs/l/e/m.a(String)`. Only `Client` construction and the render/update call remain. Therefore
terms such as announcement, broadcast, ticker or notification are not proven. They stay
unnamed rather than lowering the semantic standard.

## Naming boundary

`InteractiveModelHighlight` (**0.998**) and `InteractiveModelHighlightRegistry` (**0.997**)
are descriptive exact-behavior recovery names. They are not claims that original developer
identifiers survived ProGuard.

## Acceptance boundary

Chat 2 does not promote R218. Main/Core may accept either proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_DB704E01C67994C03183`.

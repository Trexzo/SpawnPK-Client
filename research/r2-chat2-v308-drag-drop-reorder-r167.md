# Chat 2 — exact-v308 drag-and-drop reorder Swing component R167

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R167 is a separate non-canonical class-only review for a self-contained reusable Swing
drag-and-drop reorder component family.

## Deterministic review result

- candidate classes: **4**
- resolved proposals: **4**
- unresolved: **0**
- review ID: `SEMREVIEW_EF8E4FF6B73AA76704F7`
- field/method proposals: **0**

## Stable IDs

- `rs/ui/components/g` -> `CLIENT_CLASS_001069` -> `DragAndDropReorderPane`
- `rs/ui/components/g$a` -> `CLIENT_CLASS_001070` -> `DragAndDropReorderLayoutManager`
- `rs/ui/components/g$b` -> `CLIENT_CLASS_001071` -> `DragAndDropReorderMouseHandler`
- `rs/ui/components/g$c` -> `CLIENT_CLASS_001072` -> `DragAndDropReorderListener`

## Exact surviving names

The pane rejects every non-null foreign layout with the exact v308 exception:

`DragAndDropReorderPane only supports DragAndDropReorderLayoutManager`

That preserves both the pane noun and the dedicated layout-manager noun directly in the
binary.

## DragAndDropReorderPane

The class extends `JLayeredPane`.

Construction installs:

- the dedicated nested reorder layout;
- one nested `MouseAdapter` as both mouse listener and mouse-motion listener;
- a listener list for post-reorder callbacks.

The drag lifecycle is exact:

1. a left-button press records the origin when more than one child exists;
2. movement must exceed `DragSource.getDragThreshold()` before a drag starts;
3. the grabbed child moves to `DRAG_LAYER`;
4. its free screen position follows the mouse;
5. intersection with sibling bounds and sibling midpoints determines the new list position;
6. the pane revalidates, letting the vertical layout reorder non-dragged children;
7. release restores the child to `DEFAULT_LAYER` at the selected component position;
8. every registered listener receives the moved `Component`.

The pane's layout setter explicitly permits only its dedicated reorder layout.

## DragAndDropReorderLayoutManager

The nested layout class extends `BoxLayout` with **Y_AXIS**.

During an active drag it temporarily places the dragged child back into the default layer,
runs ordinary vertical BoxLayout positioning, restores the child to the drag layer, then
restores its free-drag location.

This lets the siblings reorder normally while the dragged component remains visually under
the pointer.

## DragAndDropReorderMouseHandler

The nested `MouseAdapter` owns the complete pointer lifecycle:

- `mousePressed` arms a left-button drag;
- `mouseDragged` applies the platform drag threshold and updates reordering;
- `mouseReleased` finalizes the drag.

Every branch delegates exclusively into the enclosing pane.

## DragAndDropReorderListener

The public nested interface is a one-method functional callback over
`java.awt.Component`.

The pane exposes add/remove operations for these listeners and invokes each listener only
after a drag completes, passing the reordered component.

## Usage boundary

Exact class-reference scanning finds no project class outside this four-class family
referencing `rs/ui/components/g`.

R167 therefore names the family only as a reusable Swing primitive. It does **not** infer a
specific sidebar, plugin, settings page or other higher-level feature consumer.

## Naming boundary

The pane and layout-manager names are grounded directly in a surviving v308 literal and are
scored **0.999**.

The mouse-handler and listener names describe exact helper behavior at **0.998**; their
original nested source identifiers do not survive.

R167 remains class-only.

## Acceptance boundary

Chat 2 does not promote R167. Main/Core may accept any proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_EF8E4FF6B73AA76704F7`.

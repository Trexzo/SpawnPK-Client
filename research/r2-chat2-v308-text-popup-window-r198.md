# Chat 2 — exact-v308 TextPopupWindow R198

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R198 is a separate non-canonical class-only review for an exact readable class identity
that survives directly in v308.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_527E4D7379140F46586A`
- field/method proposals: **0**

## Stable ID

`rs/tools/TextPopupWindow` -> `CLIENT_CLASS_000995` -> `TextPopupWindow`

The semantic name is not reconstructed from neighboring behavior: the exact class path
already preserves `TextPopupWindow`.

## Exact window behavior

The class directly extends:

`javax.swing.JFrame`

Its constructor accepts:

- a title String;
- one text-writer strategy.

It then:

- calls `setTitle(...)`;
- sets close operation **3**;
- creates a dedicated text pane;
- wraps that pane in `JScrollPane`;
- places it in the frame center;
- sets the window to **989 x 571**;
- makes the window visible.

## Exact text surface

The owned text pane is configured as:

- non-editable;
- caret-visible;
- selection-visible;
- focus-aware.

The class exposes that pane through a public accessor returning `JTextPane`.

Its public String append/update method obtains the pane's `StyledDocument` and delegates
the supplied text plus `SimpleAttributeSet` to the configured writer strategy.

The constructor also installs a Ctrl+F key binding and related focus helpers around the
text surface.

This is therefore exactly a reusable styled-text popup window.

## Naming boundary

`TextPopupWindow` is **0.999** because the readable identity survives literally in the
exact v308 class name and the complete JFrame/JTextPane responsibility agrees with it.

R198 does not assign semantic names to its anonymous/nested helper classes; those remain
separate until independently justified.

## Acceptance boundary

Chat 2 does not promote R198. Main/Core may accept this proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_527E4D7379140F46586A`.

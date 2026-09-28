# Chat 2 — exact-v308 TextSearchWindow R200

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R200 is a separate non-canonical class-only review for the search window nested under the
exact R198 `TextPopupWindow`.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_F9DDD77407DE5A87FEFB`
- field/method proposals: **0**

## Stable ID

`rs/tools/TextPopupWindow$a`
-> `CLIENT_CLASS_000996`
-> `TextSearchWindow`

The stable ID is the deterministic exact-v308 R1 baseline identity.

## Exact search-window surface

The class directly extends `javax.swing.JFrame`.

Its setup path creates:

- a `JTextField`;
- a `JButton` with exact label `Search`;
- exact frame title `Search for text`;
- `FlowLayout`;
- a **300 x 75** window.

The window is centered relative to its enclosing `TextPopupWindow`, the Search button is
installed as the root pane's default button, and the initial search position comes from the
parent text pane's current caret position.

## Exact parent relationship

The nested class stores its enclosing R198 `TextPopupWindow`.

Searches are performed against that parent's `JTextPane` document, so this is not a
standalone arbitrary search utility.

## Exact search behavior

The Search action:

1. reads the search-field text;
2. lowercases both the query and document text;
3. searches from the stored position;
4. wraps to position zero when needed;
5. obtains the matching model-to-view rectangle;
6. scrolls the parent text pane to the match;
7. sets the caret to the match start;
8. extends selection to the match end;
9. advances the stored position for the next search.

That is a complete text-find window contract rather than a generic dialog.

## Exact cancel behavior

Escape is mapped on the root pane to exact action key:

`Cancel`

The bound action disposes this search JFrame.

## Naming boundary

`TextSearchWindow` is descriptive at **0.998**.

The nested original source name is stripped, but the exact frame title, Search control,
parent TextPopupWindow relationship, document-find algorithm and Escape lifecycle all agree
on the role.

R200 deliberately does not assign semantic identities to the small action/focus helper
classes used by the window.

## Acceptance boundary

Chat 2 does not promote R200. Main/Core may accept this proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_F9DDD77407DE5A87FEFB`.

# Chat 2 — exact-v308 historical ComboBoxListRenderer source recovery R229

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R229 recovers the final unreviewed real top-level class in the legacy RuneLite
`net.runelite.client.ui.components` surface.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_204D3C4C23274DD2FC85`
- field/method proposals: **0**

## Stable ID

- `rs/ui/components/c` -> `CLIENT_CLASS_001065` -> `ComboBoxListRenderer`

## Exact bytecode identity

Exact v308 preserves the old generic Swing renderer shape:

- `final class <T> extends JLabel implements ListCellRenderer<T>`;
- selected rows use the dark-gray client palette and white foreground;
- unselected rows use the list background and light-gray client palette;
- border is exactly `EmptyBorder(5, 5, 5, 0)`;
- enum values pass through the RuneLite title-case helper;
- other values use `toString()`;
- the label text is written and the renderer returns itself.

## Historical RuneLite provenance

RuneLite source at `8118d9d7b9f8129625b148a7b8d46cb735a66890` contains exactly
`net.runelite.client.ui.components.ComboBoxListRenderer<T>` with this implementation.

Commit `97fe0928e973f3addd13620edf22a5c486bd2ef5` later renamed/reworked the file into
`TitleCaseListCellRenderer`, replacing the custom JLabel/ListCellRenderer implementation
with DefaultListCellRenderer. That later source shape does not match v308; the historical
name does.

## Artifact boundary

Adjacent `rs/ui/components/h` and `rs/ui/components/t` are compiler-generated helper
classes, while `j/l/m/n/o/p` are listener helpers attached to already-reviewed
FlatTextField/IconTextField classes. R229 does not invent source-level names for them.

## Acceptance boundary

Chat 2 does not promote R229. Main/Core may accept it only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_204D3C4C23274DD2FC85`.

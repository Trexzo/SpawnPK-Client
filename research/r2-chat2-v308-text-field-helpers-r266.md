# Chat 2 — exact-v308 text-field helper family R266

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic review result

- `rs/ui/components/j` -> `CLIENT_CLASS_001075` -> `FlatTextFieldHoverMouseListener`
- `rs/ui/components/l` -> `CLIENT_CLASS_001078` -> `IconTextFieldHoverMouseListener`
- `rs/ui/components/m` -> `CLIENT_CLASS_001079` -> `IconTextFieldSuggestionListDataListener`
- `rs/ui/components/n` -> `CLIENT_CLASS_001080` -> `IconTextFieldSuggestionPopupFocusListener`
- `rs/ui/components/o` -> `CLIENT_CLASS_001081` -> `IconTextFieldContextButtonDocumentListener`
- `rs/ui/components/p` -> `CLIENT_CLASS_001082` -> `IconTextFieldRhsButtonHoverMouseListener`
- review: `SEMREVIEW_A54C5B65195B41E92300`
- unresolved: **0**
- field/method proposals: **0**

## Exact-v308 behavior

R163 already recovers `rs/ui/components/k` as `IconTextField`; R228 recovers
`rs/ui/components/i` as `FlatTextField`.

The six classes in this batch are live anonymous/helper adapters owned exclusively by those
two reviewed components.

`rs/ui/components/j` is FlatTextField's hover adapter. It suppresses hover while blocked,
applies the configured hover background without replacing the saved base color, and restores
the base background on exit.

`rs/ui/components/l` is IconTextField's shared hover adapter attached to both the wrapped
FlatTextField and its inner JTextField.

`rs/ui/components/m` is the suggestion-model ListDataListener; all three callbacks refresh
context-button visibility.

`rs/ui/components/n` is the suggestion-popup FocusAdapter; focus loss hides the popup,
clears selection, and exact v308 additionally resets SubstanceListUI rollover state.

`rs/ui/components/o` is the text DocumentListener; all three callbacks refresh the same
context-button state.

`rs/ui/components/p` is created only by the RHS-button factory; it swaps button foreground
on hover and forwards enter/exit events into FlatTextField.

RuneLite FlatTextField/IconTextField source independently preserves these same anonymous
listener roles and control-flow shapes.

## Naming boundary

All six names are descriptive source-parity names for anonymous/helper classes. No proposal
claims a verbatim original anonymous Java identifier.

## Acceptance boundary

R266 remains class-only and non-canonical. Chat 2 performs no semantic acceptance.

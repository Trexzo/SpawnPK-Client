# Chat 2 — exact-v308 teleport shortcut interface R460

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/n/c/ak` -> `CLIENT_CLASS_000612` -> `TeleportShortcutInterface`
- proposal: `SEMPROP_127FE6F0B20471EF1471`
- review: `SEMREVIEW_7EF4BD836D86C20832F5`

## Exact surface

Root widget: **48999**

The builder creates a compact panel with exactly three destination actions:

- `Edgeville teleport`
- `Home teleport`
- `Bounty teleport`

plus the close-window control.

The three buttons are laid out side-by-side and use the same presentation resource family.
There is no dynamic destination list, packet handler, requirements table or second domain.

## Distinction from R445

R445 already recovers `TeleportSelectionInterface`, a general scrollable teleport browser
with selectable destination rows.

R460 is a separate fixed three-destination shortcut surface, so
`TeleportShortcutInterface` avoids both duplication and a stronger unsupported product noun.

## Withheld residual

`rs/n/c/t` remains unnamed.

Exact v308 proves a live 600-row selectable text list under root 51318, but the only literal
is `Select` and the external owner is only the central interface registry. Widget/root
searches did not recover a safe domain noun.

Compiler/no-op residuals `rs/n/c/e`, `rs/n/c/aB`, and `rs/n/c/aR` also remain unnamed.

R460 remains non-canonical Chat 2 semantic research only.

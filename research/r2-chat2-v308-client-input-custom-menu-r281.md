# Chat 2 — exact-v308 client input and custom menu family R281

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic result

- `rs/j/a/b` -> `CLIENT_CLASS_000303` -> `ClientInputManager`
- `rs/j/a/d` -> `CLIENT_CLASS_000305` -> `ClientInputRequest`
- `rs/j/a/d$a` -> `CLIENT_CLASS_000306` -> `ClientInputType`
- `rs/j/b/a` -> `CLIENT_CLASS_000308` -> `CustomMenuSubmenu`
- `rs/j/b/d` -> `CLIENT_CLASS_000312` -> `CustomMenuManager`
- review: `SEMREVIEW_E5F3C409B85AAE7D0999`
- unresolved: **0**
- member proposals: **0**

## Input subsystem

`ClientInputManager` owns the active `ClientInputRequest` for one Client. The request defaults to **Enter text:**, stores the current text and callback, and opening it drives the Client into input mode 6. Exact Client render/key paths read the active request only in that mode.

`ClientInputType` is self-identifying in exact-v308 bytecode: **TEXT**, **AMOUNT**, **USERNAME**. Client key handling switches on those exact values to enforce the corresponding input behavior.

## Custom-menu subsystem

R12 already recovered `rs/j/b/b` as `CustomMenuEntry` from its exact self-identifying toString.

`CustomMenuSubmenu` composes up to ten of those reviewed leaf entries and tracks parent menu index, layout geometry and the hovered child. `CustomMenuManager` owns indexed callback/submenu maps and mutates the Client's parallel menu arrays while preserving those mappings. Its default submenu parent label is the exact literal **Choose Sub-Option**.

## Deliberate exclusions

R281 leaves the empty package-marker classes, the no-op abstract input base, the unused TOP/BOTTOM/BEFORE_LAST enum family, and unrelated `rs/j` root class unnamed until their precise roles are independently fixed.

## Acceptance boundary

R281 is non-canonical research only. It describes exact-v308 responsibilities and performs no semantic acceptance or source rewrite.

# Chat 2 — exact-v308 click-text selection interface R297

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic result

- `rs/n/c/t` -> `CLIENT_CLASS_000673` -> `ClickTextSelectionInterface`
- review: `SEMREVIEW_DD7855D940FA265CE924`
- unresolved: **0**
- member proposals: **0**

## Exact-v308 contract

The builder owns root **51318** and creates a **600-row** selectable text range:

- widgets **51320..51919**
- exact action text **Select**
- hover/click state enabled
- inserted into scrolling child **51319**

Client also preserves the exact command:

`CLEAR_CLICK_TEXT_INT`

and handles it by iterating exactly **51320..51919** and clearing each row's text.

That fixes the class as a generic runtime-populated clickable-text selection interface. R297 deliberately does not assign a gameplay-specific purpose because exact v308 does not expose one.

## Boundary

R297 is non-canonical semantic research only. No semantic acceptance, source rewrite or source materialization is performed.

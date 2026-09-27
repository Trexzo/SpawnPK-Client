# Chat 2 — exact-v308 raid affliction-tome progress overlay R300

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic result

- `rs/n/c/d/f` -> `CLIENT_CLASS_000656` -> `RaidAfflictionTomeProgressOverlay`
- review: `SEMREVIEW_B7F7FF78C1095A1B019B`
- unresolved: **0**
- member proposals: **0**

## Exact-v308 contract

The existing `RaidInterfacePacketHandler` selector **6** reads one integer and sends it directly to the singleton `rs/n/c/d/f` instance through `a(int)`.

The raid-party interface places widget **32465** as `raids/affbar1` beside the exact controls **Add affliction tome(s)** and **Remove affliction tome(s)**. The raid root then registers `rs/n/c/d/f` as the overlay bound to that widget.

The overlay itself:

- lazily loads `raids/affbar2`;
- renders the packet-driven value as a color-staged `x/5` label;
- exposes completion when the value reaches at least **5**;
- emits the same affliction-bar particle presentation as progress changes.

Together, the packet flow, widget placement, exact affliction controls and resource family fix the role as the raid affliction-tome progress overlay.

## Deliberate exclusions

`rs/n/c/d/g` remains unnamed. Its rendering mechanics are clear, but its domain noun is not yet strong enough to promote merely because it sits in the same raid package.

R300 is non-canonical semantic research only. No semantic acceptance, source rewrite or source materialization is performed.

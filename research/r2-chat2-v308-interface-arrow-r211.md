# Chat 2 — R211 interface-arrow duplicate-owner correction

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Correction

R211 does **not** retain a semantic review.

The attempted R211 batch targeted the exact interface-arrow family:

- `rs/l/f/a/i/b` / `CLIENT_CLASS_000470`
- `rs/l/f/a/i/d` / `CLIENT_CLASS_000472`
- `rs/l/f/a/i/e` / `CLIENT_CLASS_000473`
- `rs/l/f/a/i/g` / `CLIENT_CLASS_000475`

Those owners were already reviewed in **R138**, review:

`SEMREVIEW_53E67568D36705B68452`

with retained names:

- `InterfaceArrowOverlay`
- `InterfaceArrowPacketHandler`
- `InterfaceArrowDirection`
- `InterfaceArrowSection`

The R211 no-overlap test correctly failed. Chat 2 must not create a second semantic review
for those stable owners.

## New corroborating evidence recovered during R211

The exact-v308 audit still adds useful provenance to the existing R138 identities:

- the overlay blink path is explicitly gated by `Client.ff % 20 < 10`;
- Adventure Book creates a claim pointer on widget `30390` with direction `DOWN`
  and offsets `(35, -30)`, then marks it auto-dismissable;
- ScriptPacket 24 operations were re-confirmed as clear/create/section-or-target/default-widget
  placement operations;
- the main gameframe path consumes the six-value section state while the arrow blink phase
  is active and draws the RIGHT arrow by the corresponding sidebar/gameframe destination;
- the developer-command path independently accepts an interface widget plus
  `InterfaceArrowDirection.valueOf(...)` and creates the same overlay.

The R211 draft called `rs/l/f/a/i/g` `InterfaceArrowTarget`. R138 already names it
`InterfaceArrowSection`, grounded in the exact enum literals:

- `ACHIEVEMENT`
- `EQUIPMENT`
- `INVENTORY`
- `MAGIC`
- `MISC`
- `SETTINGS`

R211 therefore does **not** supersede that name. If Main/Core ever prefers `Target` over
`Section`, that must be an explicit correction to R138, not a duplicate semantic owner.

## Retained R211 status

- retained semantic candidate file: **none**
- retained semantic review file: **none**
- retained semantic test: **none**
- retained review ID: **none**
- new proposal count: **0**
- unresolved: **0**

The research note is retained so the additional exact evidence and withholding reason are
not lost.

## Acceptance boundary

R211 performs no semantic acceptance and creates no acceptance spec.

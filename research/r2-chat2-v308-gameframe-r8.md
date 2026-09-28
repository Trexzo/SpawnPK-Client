# Chat 2 — exact-v308 gameframe semantic resolution R8

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R8 resolves two classes that were initially held in ambiguity triage. The resolution comes
from exact interface-root joins, not from neighboring package names.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_EEC5926DB7B003A5F9CE`

## `rs/n/c/Y` -> `GameframeNavigationInterface`

Stable ID: `CLIENT_CLASS_000571`

Exact evidence:

- builds root **32000**;
- builds the gameframe tab sprite/navigation controls;
- exact click routing maps:
  - Achievements -> **44100**
  - Account Information -> **638**
  - Knowledgebase -> **64600**
  - World Events -> **40087**
  - PK Ratings -> **40403**
- manages selected/unselected gameframe tab sprites.

This proves a multi-destination gameframe navigation role rather than any one content tab.

## `rs/n/c/aa` -> `AccountInformationInterface`

Stable ID: `CLIENT_CLASS_000602`

Exact evidence:

- the `Account Information` navigation action above routes to root **638**;
- `rs/n/c/aa.a()` directly obtains and populates root **638**;
- the content includes Achievement Diary, Monster drop tables and Hotspot presentation.

The exact route-to-root join is sufficient to identify the owning content interface.

## Acceptance boundary

These are still non-canonical review proposals. Chat 2 does not accept them.

Main/Core may accept either/both through an explicit acceptance spec bound to
`SEMREVIEW_EEC5926DB7B003A5F9CE`.

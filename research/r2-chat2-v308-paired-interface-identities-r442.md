# Chat 2 — exact-v308 paired interface identities R442

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/n/c/aO` -> `CLIENT_CLASS_000590` -> `ShopTabInterface`
- `rs/n/c/q` -> `CLIENT_CLASS_000670` -> `ClanChatInterface`
- `rs/n/c/H` -> `CLIENT_CLASS_000553` -> `EquipmentStatsInterface`
- review: `SEMREVIEW_28AB359108917C39768E`

## ShopTabInterface

Exact literals include:

- `Right-click on shop`
- `Select shop tab`
- `Tab 1` .. `Tab 5`
- `Main stock`

R129 already fixes sibling `rs/n/c/aP` as `ShopTabInterfacePacketHandler`, providing an
independent structural join for this interface name.

## ClanChatInterface

This builder is the live clan-chat panel with:

- Join Chat
- Clan Setup
- Clan Chat (0/100)
- talking-in state
- owner state
- Manage clan member

R2 already owns `rs/n/c/p` as `ClanChatSetupInterface`, so this class is the distinct
chat panel rather than the setup interface.

## EquipmentStatsInterface

The screen presents:

- Equip Your Character...
- Attack / Defence / Other bonuses
- Drop rate bonus
- Blood money bonus
- Range strength
- Magic damage
- Risk value

R275 already owns `rs/n/c/I` as `EquipmentInterface`; this is the separate detailed
stats/bonuses screen.

## Boundary

R442 recovers client interface identities only and makes no server-side pricing, clan-policy
or combat-formula claims.

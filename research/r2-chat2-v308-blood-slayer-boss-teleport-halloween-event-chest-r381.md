# Chat 2 — Blood Slayer, boss teleports and Halloween Event Chest R381

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/n/c/l` -> `CLIENT_CLASS_000665` -> `BloodSlayerInterface`
- `rs/n/c/o` -> `CLIENT_CLASS_000668` -> `BossTeleportationNetworkInterface`
- `rs/n/c/N` -> `CLIENT_CLASS_000560` -> `HalloweenEventChestInterface`
- review: `SEMREVIEW_56022316A4A2498C3AE5`

### BloodSlayerInterface
Root 54100 preserves `Blood Slayer`, `Choose a Task`, PvM/PK task categories, task acquisition and Blood Slayer/Slayer reward-point state.

### BossTeleportationNetworkInterface
The 604xx interface preserves the exact title `Boss Teleportation Network`, boss names/descriptions, possible drops/rewards and numbered boss teleport choices.

### HalloweenEventChestInterface
The 606xx interface owns the event-chest tier/roll/exchange widgets used by the existing R130 Halloween Event Chest overlay/packet handler and R317 widget callback. It preserves `Halloween Event 2020`, Tier I/II prize text, Roll, Exchange, token/roll progress, Event Guide and reset controls.

## Boundary
All three proposals name exact client presentation surfaces only. No task assignment, teleport eligibility, reward odds or event server rules are inferred. R381 remains non-canonical.

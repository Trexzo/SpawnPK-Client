# Chat 2 — exact-v308 high-confidence interface identities R448

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/n/c/aC` -> `CLIENT_CLASS_000578` -> `ClientOptionsInterface`
- `rs/n/c/aD` -> `CLIENT_CLASS_000579` -> `BloodFountainPerkTreeInterface`
- `rs/n/c/aE` -> `CLIENT_CLASS_000580` -> `LegendaryPetFusingInterface`
- `rs/n/c/aI` -> `CLIENT_CLASS_000584` -> `DonorPanelInterface`
- `rs/n/c/aJ` -> `CLIENT_CLASS_000585` -> `QuickPrayerSelectionInterface`
- `rs/n/c/aK` -> `CLIENT_CLASS_000586` -> `RaidPartyInvitationsInterface`
- `rs/n/c/aL` -> `CLIENT_CLASS_000587` -> `RaidPartySetupInterface`
- review: `SEMREVIEW_26542EDED094F8FEB88B`

Each class directly extends R436 `CustomInterfaceBuilder` and has exact-v308 literals/resources that fix the client screen identity.

Key anchors include:

- Client Options: graphics/ticks/zoom/fog/particles/player-lighting/shift-drop/privacy/combat-overlay/desktop-notification toggles.
- Blood Fountain: exact title `Blood Fountain Perk Tree` and the full perk catalogue.
- Pet Fusing: exact title `Legendary Pet Fusing`, `Fuse` and `Fuse pets`.
- Donor Panel: exact `Main Donor Panel`, donor zones, shop, perks and promotional rewards.
- Quick Prayer Selection: exact quick-prayer/quick-curse selection and confirmation surface.
- Raid Invitations: exact party-invitation list/selected-invitation surface.
- Raid Party Setup: exact `Raiding Party Set-up`, raid type, difficulty, party management and start/leave controls.

## Boundary

These recover client presentation identities only. No server-side purchase, raid, prayer, combat,
pet-fusion or perk-tree authority is inferred.

R448 remains non-canonical Chat 2 research only.

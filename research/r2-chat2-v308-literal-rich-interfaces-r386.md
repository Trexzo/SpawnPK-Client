# Chat 2 — literal-rich interface builders R386

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/n/c/A` -> `CLIENT_CLASS_000545` -> `ConfirmationInterface`
- `rs/n/c/D` -> `CLIENT_CLASS_000549` -> `DuelRuleLoadInterface`
- `rs/n/c/H` -> `CLIENT_CLASS_000553` -> `EquipmentStatsInterface`
- `rs/n/c/I` -> `CLIENT_CLASS_000554` -> `EquipmentTabInterface`
- `rs/n/c/aC` -> `CLIENT_CLASS_000578` -> `GameOptionsInterface`
- `rs/n/c/aD` -> `CLIENT_CLASS_000579` -> `BloodFountainPerkTreeInterface`
- `rs/n/c/aF` -> `CLIENT_CLASS_000581` -> `PlankMakeAllInterface`
- `rs/n/c/aI` -> `CLIENT_CLASS_000584` -> `DonatorPanelInterface`
- `rs/n/c/aJ` -> `CLIENT_CLASS_000585` -> `QuickPrayerSelectionInterface`
- `rs/n/c/aK` -> `CLIENT_CLASS_000586` -> `RaidPartyInvitationsInterface`

Review: `SEMREVIEW_3A505D2010DD05DDF237`

## Evidence boundary

Every class in this batch is a concrete RSInterface builder with literal UI copy and/or an
asset namespace that fixes the presentation domain directly.

Highlights include:

- confirmation root 14170 with exact `Confirm` / `Please confirm your choice.`;
- duel-load controls `Load last rules` and `Load last duel`;
- equipment stats and equipment-tab surfaces;
- the full client game-options surface;
- exact `Blood Fountain Perk Tree` copy;
- construction plank Make-all choices and prices;
- the donor panel;
- quick prayer / quick curse selection;
- raid-party invitation presentation.

No class is promoted canonically and no server-side behavior is inferred from presentation
text.

R386 remains non-canonical Chat 2 semantic research.

# Chat 2 — exact-v308 high-confidence interface identities R448

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Corrected result

R448 retains **five** new semantic proposals:

- `rs/n/c/aD` -> `CLIENT_CLASS_000579` -> `BloodFountainPerkTreeInterface`
- `rs/n/c/aE` -> `CLIENT_CLASS_000580` -> `LegendaryPetFusingInterface`
- `rs/n/c/aI` -> `CLIENT_CLASS_000584` -> `DonorPanelInterface`
- `rs/n/c/aJ` -> `CLIENT_CLASS_000585` -> `QuickPrayerSelectionInterface`
- `rs/n/c/aK` -> `CLIENT_CLASS_000586` -> `RaidPartyInvitationsInterface`
- corrected review: `SEMREVIEW_CC6443C92708750E78F1`

Two attempted R448 owners were removed after reconciliation with earlier Chat 2 authority:

- `rs/n/c/aC` is already owned as `ClientSettingsInterface`; the attempted
  `ClientOptionsInterface` name was a same-owner duplicate/correction candidate, not a new class.
- `rs/n/c/aL` is already owned as `RaidPartySetupInterface`; the R448 rediscovery was an
  exact duplicate.

The retained five classes directly extend R436 `CustomInterfaceBuilder` and have exact-v308
screen literals/resources fixing their identities.

## Evidence anchors

- Blood Fountain: exact title `Blood Fountain Perk Tree` and full perk catalogue.
- Pet Fusing: exact title `Legendary Pet Fusing`, `Fuse` and `Fuse pets`.
- Donor Panel: exact `Main Donor Panel`, donor zones, shop, perks and promotional rewards.
- Quick Prayer Selection: exact quick-prayer/quick-curse selection and confirmation surface.
- Raid Invitations: exact party-invitation list/selected-invitation surface.

## Stable-ID authority

The retained IDs were revalidated from canonical R1 `seed_lineage()` authority: all exact
`rs/**` internal names sorted lexicographically over the v308 JAR. The reproduced map matches
known checkpoints including `rs/Client -> CLIENT_CLASS_000029`,
`rs/n/c/H -> CLIENT_CLASS_000553`, `rs/n/c/U -> CLIENT_CLASS_000567`, and
`rs/n/c/x/y/z -> CLIENT_CLASS_000677/000678/000679`.

## Boundary

These recover client presentation identities only. No server-side purchase, raid, prayer,
pet-fusion or perk-tree authority is inferred.

R448 remains non-canonical Chat 2 research only.

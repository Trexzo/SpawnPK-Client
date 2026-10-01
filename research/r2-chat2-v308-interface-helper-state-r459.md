# Chat 2 — custom-interface helper/state layer R459

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/n/c/B` -> `CLIENT_CLASS_000547` -> `ConfirmationDialogPacketHandler`
- `rs/n/c/K` -> `CLIENT_CLASS_000557` -> `EventActivityViewerPacketHandler`
- `rs/n/c/W` -> `CLIENT_CLASS_000569` -> `GamblingInterfacePacketHandler`
- `rs/n/c/aP` -> `CLIENT_CLASS_000591` -> `ShopTabInterfacePacketHandler`
- `rs/n/c/ah` -> `CLIENT_CLASS_000609` -> `ItemsKeptOnDeathAutoKeepPacketHandler`
- `rs/n/c/ar` -> `CLIENT_CLASS_000622` -> `MakeQuantityInterfacePacketHandler`
- `rs/n/c/ax` -> `CLIENT_CLASS_000628` -> `DonationShoppingCartEffectStateHandler`
- `rs/n/c/ay` -> `CLIENT_CLASS_000629` -> `DonationShoppingCartParticleEffectRenderer`

Review: `SEMREVIEW_E19CF6FB1FE5D33CDF45`

## Exact ScriptPacket joins

The existing exact S2C250 corpus independently fixes:

- subtype 6 -> `rs/n/c/K` -> Event Activity/token-limit state;
- subtype 9 -> `rs/n/c/ah` -> Items Kept on Death auto-keep set;
- subtype 15 -> gambling session/state;
- subtype 17 -> shop tabs;
- subtype 28 -> `rs/n/c/B` -> confirmation-dialog state;
- subtype 35 -> `rs/n/c/ar` -> Make-X quantity interface;
- subtype 36 -> `rs/n/c/ax` -> indexed enum/progress state.

Direct exact-v308 parent/consumer joins refine those structural packet roles to their
specific client presentation owners.

## Donation-cart pair

Older protocol work deliberately kept subtype 36's product noun unresolved.

Exact v308 closes only the **client-side** domain join:

- DonationShoppingCartInterface owns `rs/n/c/ax`;
- every handler selector mutates `rs/n/c/ay` effect state;
- DonationShoppingCartInterface owns/registers `rs/n/c/ay` around cart widgets;
- `ay` creates live particle objects through the client particle renderer.

That is sufficient for:

- `DonationShoppingCartEffectStateHandler`;
- `DonationShoppingCartParticleEffectRenderer`;

but not for any donation purchase, pricing or checkout business-rule claim.

## Duplicate exclusions

This batch intentionally does **not** re-propose:

- `rs/n/c/X` — already R295 `GamblingRulesSwitchedOverlay`;
- `rs/n/c/L` — already R285 `EventActivityViewerRefreshTask`;
- `rs/n/c/R` — already R286 `HotspotVoteSkipTooltipTask`;
- `rs/n/c/S` — already R286 `HotspotStatusTooltipTask`;
- `rs/n/c/P` — older `ActiveEventsInterfacePacketHandler`;
- `rs/n/c/ac` — R122 `ItemListInterface`.

R459 remains non-canonical Chat 2 semantic research only.

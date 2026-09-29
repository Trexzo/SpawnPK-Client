# Chat 2 — literal-rich interface builders R388

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/n/c/ai` -> `CLIENT_CLASS_000610` -> `KeyBindingSelectionInterface`
- `rs/n/c/aj` -> `CLIENT_CLASS_000611` -> `GameframeToolsMenuInterface`
- `rs/n/c/al` -> `CLIENT_CLASS_000613` -> `ItemLoadoutModificationInterface`
- `rs/n/c/am` -> `CLIENT_CLASS_000614` -> `LoginWelcomeEventInterface`
- `rs/n/c/an` -> `CLIENT_CLASS_000615` -> `LootingBagInterface`
- `rs/n/c/ao` -> `CLIENT_CLASS_000616` -> `LotteryInterface`
- `rs/n/c/as` -> `CLIENT_CLASS_000623` -> `MarketplaceInterface`
- `rs/n/c/at` -> `CLIENT_CLASS_000624` -> `MarketplaceSearchResultsInterface`
- `rs/n/c/au` -> `CLIENT_CLASS_000625` -> `MarketplaceListingInterface`
- `rs/n/c/az` -> `CLIENT_CLASS_000631` -> `MonsterDropSearchInterface`

Review: `SEMREVIEW_D285DDAEA5FE5834D2DF`

This batch recovers key-binding selection, the gameframe tools menu, item-loadout editing,
login/welcome-event presentation, looting bag, lottery, the three-part marketplace surface,
and monster-drop search.

Known duplicate traps such as DailyMoneyMakingInterface and CollectionLogInterface remain
untouched. R388 is non-canonical Chat 2 research only.

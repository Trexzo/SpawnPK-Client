# Chat 2 — exact-v308 IconTextField source-parity R163

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/ui/components/k` -> `CLIENT_CLASS_001076` -> `IconTextField`
- `rs/ui/components/k$a` -> `CLIENT_CLASS_001077` -> `Icon`
- proposals: **2**
- unresolved: **0**
- review: `SEMREVIEW_74D08E0F75A56AD51744`

Exact-v308 structure matches public RuneLite
`net.runelite.client.ui.components.IconTextField` at commit
`7e6d9ac8138be3aa165f88da527ad5a5e6a5d21b`: icon JLabel, FlatTextField-equivalent,
clear/suggestion buttons, suggestion popup/model, hover behavior and the same icon setter.

The nested enum is exact:

- `SEARCH` -> `search.png`
- `LOADING` -> `loading_spinner.gif`
- `LOADING_DARKER` -> `loading_spinner_darker.gif`
- `ERROR` -> `error.png`

Current SpawnPK consumers include the reviewed PluginHubPanel and TradingPostSearchPanel.

Chat 2 does not promote R163. Main/Core acceptance remains explicit and review-bound.

# Chat 2 — R14 source-identity correction after R238

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

Historical RuneLite source at `68c819924cfd6bfb4848c71f74c121109f289d5a` resolves two older descriptive R14 labels:

- `rs/s/b/g` / `CLIENT_CLASS_000867`: `ConfigurationPlugin` -> `ConfigPlugin`
- `rs/s/b/w` / `CLIENT_CLASS_000883`: `PluginConfigurationRootPanel` -> `TopLevelConfigPanel`

The source match is exact across plugin descriptor/lifecycle/provider/resource behavior for
`ConfigPlugin`, and across PluginPanel/CardLayout/EventBus/material-tab/resource/forwarding
behavior for `TopLevelConfigPanel`.

Proposal count remains **13**. No semantic acceptance is performed.

- superseded review: `SEMREVIEW_10B38C13D2C28216E473`
- corrected review: `SEMREVIEW_327683188A4DACD87309`

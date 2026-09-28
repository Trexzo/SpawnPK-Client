# Chat 2 — exact-v308 configuration/plugin-list semantics R13 (source-corrected)

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

This document supersedes the original descriptive R13 labels for four configuration UI
classes after exact RuneLite source identities were recovered.

## Corrected deterministic review

- candidate classes: **10**
- resolved proposals: **10**
- unresolved: **0**
- corrected review ID: `SEMREVIEW_3A84CE667D865C655D92`
- superseded review ID: `SEMREVIEW_D9B003FC41F9A1D776D9`
- field/method proposals: **0**

## Corrected configuration identities

| Raw class | Stable ID | Corrected source identity |
| --- | --- | --- |
| `rs/s/b/a` | `CLIENT_CLASS_000861` | `ConfigPanel` |
| `rs/s/b/n` | `CLIENT_CLASS_000874` | `PluginConfigurationDescriptor` |
| `rs/s/b/o` | `CLIENT_CLASS_000875` | `PluginListItem` |
| `rs/s/b/q` | `CLIENT_CLASS_000877` | `PluginListPanel` |
| `rs/s/b/u` | `CLIENT_CLASS_000881` | `PluginToggleButton` |

The unchanged `PluginConfigurationDescriptor` already self-identifies in its exact
toString form.

### ConfigPanel

Exact v308 builds descriptor-driven config controls and uniquely owns the configuration
back/edit resources and reset-confirmation flow. RuneLite source at `68c819924cfd6bfb4848c71f74c121109f289d5a` confirms
the source identity `ConfigPanel`.

### PluginListItem

Exact v308 is a JPanel implementing SearchablePlugin with one plugin descriptor, keyword
tokens, star pin control, config action and plugin toggle. The unique `star_on.png`,
`Pin plugin`, `Unpin plugin` and `Edit plugin configuration` literals match RuneLite
`PluginListItem`.

### PluginListPanel

Exact v308 owns plugin/config managers, fake descriptors, the muxer, search box, scrolling
list, pinned-plugin persistence and filtering/rebuild lifecycle. The unique
`pinnedPlugins` key and whole-class surface match RuneLite `PluginListPanel`.

### PluginToggleButton

Exact v308 is the reusable on/off JToggleButton with switcher images, conflict text and
Enable/Disable tooltips, matching RuneLite `PluginToggleButton`.

The older names `PluginConfigurationPanel`, `PluginHubPluginEntry`,
`PluginHubPanel`, and `PluginEnableToggleButton` were reasonable descriptive labels
but are now superseded by stronger source-name evidence.

## Other R13 proposals

Item ID Search and Trading Post proposals are unchanged.

## Acceptance boundary

Chat 2 does not promote corrected R13. Main/Core may accept proposals only through an
explicit `semantic_acceptance_spec` bound to `SEMREVIEW_3A84CE667D865C655D92`.

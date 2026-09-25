# Chat 2 — exact-v308 Developer Tools plugin panel / widget type R196

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R196 is a separate non-canonical class-only review for two previously unnamed classes in the
already-recovered Developer Tools package.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_A24A3EDEADBED527A066`
- field/method proposals: **0**

## Stable IDs

- `rs/s/c/g` -> `CLIENT_CLASS_000894` -> `DeveloperToolsPluginPanel`
- `rs/s/c/h` -> `CLIENT_CLASS_000895` -> `DevToolsWidgetType`

## Existing Developer Tools authority

Earlier reviews already recover the surrounding feature, including:

- `InterfaceDeveloperToolsConfig`;
- `DeveloperToolsPlugin`;
- `DeveloperToolsSidebarPanel`;
- `DevToolsWidgetOverlay`;
- `DevToolsWidgetDisplay`.

R196 fills two remaining exact package roles without renaming those existing proposals.

## DeveloperToolsPluginPanel

Reviewed `DeveloperToolsPlugin` obtains `rs/s/c/g` from the injector during startup.

It then builds the exact navigation button:

`Developer Tools`

with:

`devtools_icon.png`

and binds `rs/s/c/g` as that button's PluginPanel before registering it with ClientUI.

The panel itself directly extends the PluginPanel base and owns one CardLayout.

Its two exact tool cards are:

- `Recolor models` using `palette.png`, backed by the reviewed
  `DeveloperToolsSidebarPanel`;
- `Interfaces` using `interface.png`, backed by the Developer Tools plugin configuration
  component.

Activation and deactivation delegate only to the currently selected child panel.

This is therefore the plugin's top-level navigation panel, distinct from the narrower
DeveloperToolsSidebarPanel.

## DevToolsWidgetType

Reviewed `InterfaceDeveloperToolsConfig` exposes:

- key: `showTypes`;
- title: `Display widget types`;
- type: `Set<rs/s/c/h>`;
- default: all `rs/s/c/h.values()`.

The exact enum values are:

- `SCROLL`;
- `BTN`;
- `TXT`;
- `RECT`;
- `SPRT`;
- `DRPDWN`;
- `INV`.

Each value stores the corresponding client widget-type id plus its developer-overlay
presentation color.

Reviewed `DevToolsWidgetOverlay` maps each live widget's exact type integer through the
enum's id map, filters against the configured Display widget types Set, and passes the enum
into reviewed `DevToolsWidgetDisplay`.

That value object preserves the self-identifying component:

`type=…`

so the enum's responsibility is exact.

## Naming boundary

Both names are descriptive readable replacements, not claims about stripped developer source
names.

- `DeveloperToolsPluginPanel`: **0.999**
- `DevToolsWidgetType`: **0.999**

R196 remains class-only and non-canonical.

## Acceptance boundary

Chat 2 does not promote R196. Main/Core may accept either proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_A24A3EDEADBED527A066`.

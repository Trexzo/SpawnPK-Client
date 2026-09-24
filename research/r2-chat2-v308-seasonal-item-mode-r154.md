# Chat 2 — exact-v308 seasonal item mode R154

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R154 resolves the second sibling enum from the paired `ground_mode` setting left open by
R84 and deliberately separated from R153 `WorldTheme`.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_26EFDAFE2D0D62B5BA26`
- field/method proposals: **0**

## Stable ID

`rs/f/a$d` -> `CLIENT_CLASS_000171` -> `SeasonalItemMode`

## Exact enum contract

The constants are:

- `NONE`;
- `SPRING`;
- `SUMMER`;
- `HWEEN`;
- `DARK_WINTER`;
- `WINTER`.

Unlike R153 `WorldTheme`, this enum has no RGB/color payload.

## Exact consumer boundary

The compiled reference surface is narrow.

Outside R83 `ClientSettings`, the enum is consumed by `ItemDefinition`.

It is not referenced by:

- FloorDefinition;
- NpcDefinition;
- ObjectDefinition;
- ObjectManager/region rendering;
- interface builders;
- the GPU/software rendering stack.

That separates it cleanly from the world-wide R153 theme enum.

## ItemDefinition behavior

`ItemDefinition` branches on non-default seasonal values and applies hard-coded
season-specific definition/model override tables for selected item ids.

Exact v308 contains active override branches for:

- `SPRING`;
- `HWEEN`;
- `DARK_WINTER`;
- `WINTER`.

`NONE` is the default. `SUMMER` exists as an enum value even though the inspected
v308 ItemDefinition override path does not expose an equivalent active branch.

The class therefore represents seasonal item-definition presentation state rather than the
whole-world color/object/NPC theme.

## Paired persistence contract

ClientSettings persists:

`ground_mode=<WorldTheme>.<SeasonalItemMode>`

R153 resolves the first component.

R154 resolves the second component.

v308 initializes the second component to `NONE`. During settings restoration, the
persisted first component is restored only when the saved second-component name matches the
current seasonal-item mode. This makes the second enum part of the compatibility context for
the user-selectable world theme.

## Naming boundary

`SeasonalItemMode` is **0.998**.

The enum values and ItemDefinition-only consumer boundary are exact. Confidence remains
below 0.999 because v308 does not expose every non-default activation path for this setting.

The name is descriptive readable recovery, not a claim of the original source identifier.

## Acceptance boundary

Chat 2 does not promote R154. Main/Core may accept this proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_26EFDAFE2D0D62B5BA26`.

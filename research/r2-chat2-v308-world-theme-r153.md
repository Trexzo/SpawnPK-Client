# Chat 2 — exact-v308 world theme enum R153

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R153 resolves one of the two sibling `ground_mode` enums deliberately withheld by R84.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_AD3FFFEAA4722512E54A`
- field/method proposals: **0**

## Stable ID

`rs/f/a$b` -> `CLIENT_CLASS_000169` -> `WorldTheme`

## Exact enum contract

The exact constants are:

- `NORMAL`;
- `WINTER`;
- `DARK_WINTER`;
- `HALLOWEEN`;
- `SUMMER`.

Every non-`NORMAL` enum value also stores one fixed RGB color value.

## Live command surface

The Client command parser maps exact user commands into this enum:

- `winter` -> `WINTER`;
- `hween` -> `HALLOWEEN`;
- `summer` -> `SUMMER`;
- `darkwinter` / `darkxmas` -> `DARK_WINTER`.

Issuing the same active command toggles back to `NORMAL`.

The selected value is stored in ClientSettings and triggers the corresponding configuration
refresh path.

## World-wide consumers

This enum is not limited to one UI or asset.

Exact references occur in:

- `FloorDefinition`;
- `NpcDefinition`;
- `ObjectDefinition`;
- `ObjectManager` / region-building code;
- adjacent world-definition/render preparation.

FloorDefinition directly consumes the enum's RGB payload as a replacement floor color for
eligible surfaces.

NpcDefinition/ObjectDefinition and region consumers branch on the same theme constants to
apply theme-specific definition/model/object adjustments.

This establishes a whole-world visual theme rather than an item-only or ground-color-only
setting.

## Persistence

R83 `ClientSettings` writes:

`ground_mode=<first enum>.<second enum>`

R153 identifies the first enum only.

Its default is `NORMAL`; the configured override is omitted when the active value matches
that default.

## Deliberate sibling boundary

R153 does **not** name `rs/f/a$d`.

That enum preserves:

- `NONE`;
- `SPRING`;
- `SUMMER`;
- `HWEEN`;
- `DARK_WINTER`;
- `WINTER`.

Its exact compiled consumers are concentrated in `ItemDefinition`, where it selects
season-specific item-definition/model override tables. Although that behavior is clearly
seasonal, the precise semantic noun and lifecycle are less independently anchored than
`WorldTheme`, so it remains withheld.

## Naming boundary

`WorldTheme` is **0.999**.

The name is descriptive readable recovery based on exact enum constants, command controls,
RGB payload and world-wide consumers. It is not claimed as a surviving original developer
identifier.

## Acceptance boundary

Chat 2 does not promote R153. Main/Core may accept this proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_AD3FFFEAA4722512E54A`.

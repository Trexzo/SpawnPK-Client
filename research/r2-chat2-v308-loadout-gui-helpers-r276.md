# Chat 2 — exact-v308 loadout GUI helpers R276

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic result

- `rs/gui/b/a/A` -> `CLIENT_CLASS_000207` -> `LoadoutSkillLevelEditor`
- `rs/gui/b/a/a` -> `CLIENT_CLASS_000210` -> `LoadoutCloneButtonFactory`
- `rs/gui/b/a/y` -> `CLIENT_CLASS_000234` -> `LoadoutPropertiesFrame`
- review: `SEMREVIEW_7B73A214B566FA51724B`
- unresolved: **0**
- field/method proposals: **0**

## Authority correction before R276

An initial R276 attempt rediscovered four interfaces already present in the R2 seed review. Its dedicated pre-R276 overlap test correctly detected that condition, so the entire attempted batch was removed in commit `28b99a1dd081e01c4aaa76c94c2eaa87f0165e18` without weakening any guard. R2 is therefore included explicitly in the overlap boundary for this corrected batch.

## Exact-v308 evidence

### LoadoutSkillLevelEditor

`rs/gui/b/a/A` is a JFrame whose title is generated as **Set <skill> level**. The skill-index switch resolves to **Attack, Range, Strength, Prayer, Defence, Magic, Hitpoints**. Submitted input is parsed as an integer, clamped to **1..99**, written into the selected slot of the active loadout stat array, the loadout UI is refreshed, and the frame closes. `rs/gui/b/p` creates this frame directly from the active loadout model and clicked skill index.

### LoadoutCloneButtonFactory

`rs/gui/b/a/a` constructs one JButton labelled **Clone**, loads `assets/gui/clone.png`, and installs the exact tooltip:

> Take the items you're equipping in game, and set them as the current active loadout.

The factory takes the loadout window `rs/gui/b/h`, installs `rs/gui/b/a/b` as the action listener, and `rs/gui/b/h` directly requests this button while assembling its controls.

### LoadoutPropertiesFrame

`rs/gui/b/a/y` is a JFrame used by both create and rename paths. The create caller opens it as **Name Your Loadout** with action **Create**; the rename caller opens the same frame with action **Rename**. The frame edits the loadout name and exposes explicit **Color:** and **Icon:** selectors, including **None (Default)** and named color choices. Callers read those three values back into the loadout record.

## Stable-ID check

The stable IDs are the exact positions of these internal names in the deterministic sorted v308 `rs/**/*.class` inventory, consistent with retained mappings such as `rs/gui/b/a/n -> CLIENT_CLASS_000223` from R274.

## Boundary

R276 remains non-canonical research. These names describe exact-v308 behavior and caller joins; no original stripped source identifiers are claimed and no semantic acceptance is performed.

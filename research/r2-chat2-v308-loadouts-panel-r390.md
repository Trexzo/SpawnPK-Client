# Chat 2 — exact-v308 Loadouts panel R390

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/gui/b/h` -> `CLIENT_CLASS_000250` -> `LoadoutsPanel`
- proposal: `SEMPROP_A804361DDF23D61A1830`
- review: `SEMREVIEW_93EC02A5042580DB5C64`

R386 already fixes `rs/s/k/a` as `LoadoutsPlugin`. Its startup creates this exact panel,
installs it as the loadout panel singleton and registers the navigation surface titled
`Loadouts`.

The panel itself extends the plugin-panel base and owns the visible Loadouts workflow. Exact
strings include:

- `Main folder`
- `Create a new loadout`
- `Delete this loadout`
- `Rename the active loadout`

Its object graph is the reviewed loadout domain: LoadoutManager, LoadoutPersistence,
DefaultLoadoutSeeder, LoadoutPreviewRenderer, LoadoutDefinition, LoadoutFolder, LoadoutIcon
and LoadoutItemEntry.

R390 is non-canonical semantic research only.

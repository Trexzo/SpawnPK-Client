# Chat 2 — exact-v308 definition reload manager R331

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/h/f` -> `CLIENT_CLASS_000294` -> `DefinitionReloadManager`
- proposal: `SEMPROP_D0513B2948BB84C051CF`
- review: `SEMREVIEW_62352781CEFAD27F9C25`

## ItemDefinition reload path

One static request flag gates the first reload path.

When triggered, exact v308:

1. resets the ItemDefinition backing loader;
2. installs/reinitializes the ItemDefinition cache loader;
3. clears ItemDefinition's definition cache;
4. invokes the client definition-reset path;
5. clears shared sprite/model caches;
6. refreshes the client and associated definition-backed resources;
7. returns true to the caller.

R28 already fixes `rs/d/k` as `ItemDefinition`.

## NpcDefinition reload path

The second request flag gates a separate NpcDefinition path.

It:

1. clears NpcDefinition model/cache state;
2. resets the static 20-entry NpcDefinition cache;
3. iterates live client NPCs;
4. re-resolves each NPC's definition by the existing id;
5. copies refreshed size/animation/movement fields back onto the live NPC;
6. refreshes dependent overlay/plugin state;
7. returns true.

R28 already fixes `rs/d/d` as `NpcDefinition`.

## Main-loop / command join

The client command dispatcher `rs/n/a` raises the two reload flags.

The main Client loop calls both DefinitionReloadManager paths after command/shortcut handling.
When either returns true, the client renders exact text `Loading - please wait.`, sleeps
briefly and exits the current loop iteration.

That establishes this class as deferred definition hot-reload coordination rather than a
generic cache helper.

R331 remains non-canonical semantic research only.

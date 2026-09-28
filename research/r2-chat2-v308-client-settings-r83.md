# Chat 2 — exact-v308 global client settings R83

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R83 is a separate non-canonical class-only semantic review batch for the exact
`settings.properties`-backed global settings authority.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_425098E7FCD7FEC3474A`
- field/method proposals: **0**

## Stable-ID verification

Core's exact `seed_lineage()` ordering over the complete `rs/` baseline gives:

- `rs/f/a` -> `CLIENT_CLASS_000167`

## `rs/f/a` -> `ClientSettings`

This class is a global static settings authority, not a feature-local config object.

The exact persisted filename is:

`settings.properties`

The save path is exposed through the surviving task key:

`SaveSettings`

and delegates to the class's private disk writer.

The writer serializes the current static values to a temporary settings file, then replaces
the persisted target. The corresponding load path opens `settings.properties` through
`java.util.Properties` and restores the static state.

Surviving keys include, among many others:

- `oldschool_graphics`
- `screen_mode`
- `show_roofs`
- `show_fog`
- `item_drag`
- `queued_item_clicks_v2`
- `player_attack_option`
- `npc_attack_option`
- `desktop_notifications`
- `timer_overlay`
- `shift_drop`
- `key_binding_<n>`
- `split_private_chat`
- `sound_effects`
- `particle_system_1`

The static surface is referenced throughout exact v308. Direct constant-pool inspection
finds more than one hundred consuming classes spanning:

- `Client`;
- cache and definition loaders;
- interface builders;
- rendering;
- plugins;
- desktop notification code;
- launcher/UI shell code;
- classic runtime helpers.

That breadth matters: this is not a plugin `Config` interface such as the R16 framework.
It is the client-wide persisted settings layer used by both the classic client and the
newer plugin/UI stack.

## Nested-type boundary

R83 names only the outer global authority.

The nested `rs/f/a$a`, `rs/f/a$b`, `rs/f/a$c` and `rs/f/a$d` values are not pulled
into this batch merely because their enclosing settings owner is now understood. They
require their own exact semantic evidence if they are ever proposed.

## Naming boundary

`ClientSettings` is a conservative semantic recovery name derived from the exact
persistence contract and runtime usage. It is not claimed as a verbatim original developer
identifier.

## Acceptance boundary

Chat 2 does not promote R83. Main/Core may accept the proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_425098E7FCD7FEC3474A`.

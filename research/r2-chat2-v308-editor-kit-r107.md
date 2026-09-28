# Chat 2 — exact-v308 SPK Editor Kit entity hierarchy R107

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R107 is a separate non-canonical class-only review for the live **SPK Editor Kit**
controller and its complete concrete entity hierarchy.

## Deterministic review result

- candidate classes: **5**
- resolved proposals: **5**
- unresolved: **0**
- review ID: `SEMREVIEW_44B7E8ED756A6FC932E8`
- field/method proposals: **0**

## Stable IDs

- `rs/l/b/a/a/a` -> `CLIENT_CLASS_000369` -> `EditorEntity`
- `rs/l/b/a/a/b` -> `CLIENT_CLASS_000370` -> `EditorItemEntity`
- `rs/l/b/a/a/c` -> `CLIENT_CLASS_000371` -> `EditorNpcEntity`
- `rs/l/b/a/a/d` -> `CLIENT_CLASS_000372` -> `EditorPlayerEntity`
- `rs/l/b/a/d` -> `CLIENT_CLASS_000378` -> `EditorKitController`

## EditorKitController

The product boundary survives directly in exact v308.

`Launcher` checks the controller's static editor-mode flag and changes the window title to:

`SPK Editor Kit`

while also changing the ordinary launcher/client UI for that mode.

The live loading controller creates exactly one:

`new rs/l/b/a/d(Client)`

stores it in the class singleton and initializes it whenever Editor Kit mode is active.
Client loop, input and camera paths later interact with that same singleton.

The class owns the Editor Kit entity list, camera/background/HUD state, graphics context,
status output and the command parser.

Global commands include:

- `npc`
- `player`
- `item`
- `delete` / `del`
- `reset` / `wipe`
- `reverse`
- `hud`
- `background` / `bg`

It also owns entity movement/animation commands and exact diagnostics including:

- `Camera position reset`
- `Camera reset!`
- `Entities cleared!`
- `Entity indices reversed!`
- `Graphics and definitions have been reset!`
- `Added @gre@NPC ...`
- `Added @gre@Player ...`
- `Set the active item to: @gre@...`

The surviving product label plus singleton lifecycle and command/render ownership support
the descriptive name `EditorKitController`.

## EditorEntity

`rs/l/b/a/a/a` is abstract.

An exact class scan finds only three concrete subclasses:

- `rs/l/b/a/a/b`
- `rs/l/b/a/a/c`
- `rs/l/b/a/a/d`

The base owns common:

- world/editor position;
- SequenceDefinition and animation-frame state;
- selection/hover state;
- entity index/order state;
- interaction/render collections.

Its shared tick lazily initializes subclass behavior, invokes the subclass render/update
hook and advances the assigned sequence frames.

It also uses the EditorKitController singleton and Client projection state directly.

## EditorItemEntity

The controller's exact `item` command:

1. parses the requested item ID;
2. resolves R28 `ItemDefinition` to print the selected item name;
3. removes the prior item entity;
4. constructs `new rs/l/b/a/a/b(itemId)`.

The subclass stores that item ID and renders it through the ItemDefinition sprite-generation
path.

This fixes it as the item-backed Editor Kit entity.

## EditorNpcEntity

The integer constructor resolves:

`NpcDefinition.c(id)`

and its model path obtains the NPC definition model.

The controller's `npc` command constructs this class, assigns its editor index/position
and inserts it into the shared entity list.

The subclass retains exact UI messages:

- `Selected @gre@NPC entity #...`
- `Deleted @red@NPC entity #...`

## EditorPlayerEntity

The `player` command constructs this subclass and inserts it into the same entity list.

The subclass constructs/owns the exact-v308 `Player` object and uses the Player model
path. Its adjacent command helper mutates appearance/equipment including named slots such
as:

- amulet;
- boots;
- cape;
- gloves;
- helmet;
- legs;
- shield;
- weapon;

plus male/female transforms.

It preserves exact UI messages:

- `Selected @gre@Player entity #...`
- `Deleted @red@Player entity #...`

## Naming boundary

These names are descriptive recovery names, not claims that the original developer source
identifiers survived.

The controller name is anchored to the exact product label `SPK Editor Kit`; the entity
names are anchored to their exact definition/model types and live command construction.

R107 deliberately does **not** name:

- NPC/player command-helper classes;
- entity comparator/sorter internals;
- timer/mesh helper records in the same package.

Those remain separate evidence questions.

## Acceptance boundary

Chat 2 does not promote R107. Main/Core may accept any subset only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_44B7E8ED756A6FC932E8`.

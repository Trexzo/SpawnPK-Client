# Chat 2 — exact-v308 Editor Kit utility command handler R110

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R110 is a separate non-canonical class-only review for the remaining live command helper in
the exact-v308 **SPK Editor Kit** package.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_DEABD93A8D21306DEBDA`
- field/method proposals: **0**
- confidence: **0.998**

## Stable ID

- `rs/l/b/a/a` -> `CLIENT_CLASS_000368` -> `EditorKitUtilityCommandHandler`

## Exact controller dispatch

R107 `EditorKitController` directly invokes:

`rs/l/b/a/a.a(originalCommand, commandName, args)`

for every entered Editor Kit command, immediately alongside the controller's own global and
entity command parser.

That proves this is a live command-dispatch helper rather than dormant debug residue.

## Exact command vocabulary

The helper recognizes only the following family:

- `col`
- `cols`
- `color`
- `colors`
- `finditem`
- `findnpc`
- `itemdef`
- `texture`
- `textures`

Those commands are tooling/inspection utilities distinct from:

- R108 typed NPC commands;
- R108 typed player commands;
- R107 ordinary entity movement/spawn/reset commands.

## Entity color tooling

The color commands iterate the live R107 `EditorEntity` list.

They can:

- reset selected color IDs;
- append one or more comma-separated color IDs;
- rebuild the entity;
- report the resulting selected-color array through EditorKitController.

This is the same selected-color state later consumed by the editor entity/model rendering
path.

## Definition search tooling

`finditem` and `findnpc` build a lowercase search phrase from the command arguments.

Arguments prefixed with `-` become exclusion terms.

The helper scans definition IDs up to 40000 and emits matching:

- ItemDefinition name + ID;
- NpcDefinition name + ID.

Matches are written through the EditorKitController output surface.

## ItemDefinition inspection/reset

`itemdef reset`:

- resets the client definition/model state;
- creates and loads a new R80 `ItemDefinitionConfigLoader`;
- clears the relevant ItemDefinition caches;
- refreshes the Editor Kit;
- emits `Item definitions reset!`.

`itemdef <id>` resolves the exact ItemDefinition and writes its internal model/debug
properties to stdout, including model IDs, rotations, zoom/offsets, equipment models,
stack arrays and recolor/retexture arrays.

## Texture tool

`texture` / `textures` switches the existing texture/debug UI into its open state and
emits:

`Textures opened`

through EditorKitController.

## Relationship to R107-R109

- R107 owns the controller and editor entity hierarchy.
- R108 owns the selected NPC/player typed command handlers.
- R109 owns notification rendering and entity distance ordering.
- R110 owns the remaining **live** utility/debug command family dispatched directly by the
  controller.

R110 still deliberately excludes `rs/l/b/a/b/b` and its enum. Their
`./debug/textures.txt` parser remains effectively self-contained/dead in exact v308 and
does not become semantic authority merely because the file format is readable.

## Naming boundary

No surviving original class noun was found.

`EditorKitUtilityCommandHandler` is descriptive exact-behavior recovery. Confidence is
0.998 because the command ownership and live controller dispatch are exact, while the
English class noun is recovered rather than source-preserved.

## Acceptance boundary

Chat 2 does not promote R110. Main/Core may accept the proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_DEABD93A8D21306DEBDA`.

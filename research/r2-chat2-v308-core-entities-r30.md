# Chat 2 — exact-v308 core entity semantics R30

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R30 is a separate non-canonical class-only semantic review batch. It does not alter
Main/Core's accepted R2 semantic authority or prior R3-R29 review batches.

## Deterministic review result

- candidate classes: **5**
- resolved proposals: **5**
- unresolved: **0**
- review ID: `SEMREVIEW_3283256A87AD65D101B6`
- field/method proposals: **0**

## Core hierarchy

- `rs/a/a` -> `Renderable`
- `rs/a/c` -> `Actor`
- `rs/a/h` -> `Model`
- `rs/a/j` -> `Npc`
- `rs/a/k` -> `Player`

The hierarchy is structurally exact:

`NodeSub -> Renderable -> Actor -> {Npc, Player}`

`Model` also extends Renderable and is the concrete geometry type consumed by R28
definitions and actor rendering.

## Renderable

The renderable base extends R25 `NodeSub`, exposes scene-render entrypoints and delegates
to a model-producing method returning `rs/a/h`. This is the classic scene-object boundary
between linked-list nodes and concrete render/model classes.

## Actor

The shared actor base owns:

- movement/path queue arrays;
- tile/world position state;
- facing and target state;
- animation/sequence state;
- combat/hit/status fields;
- movement update methods;
- world-point/polygon projection helpers.

Both Npc and Player extend it directly.

## Model

The model class owns the complete render geometry pipeline:

- vertex and face arrays;
- colors/textures/priorities/alphas;
- skin groups;
- bounds and transforms;
- sequence/frame animation application;
- projection and rasterization.

R28 Item/NPC/Object/SpotAnimation definitions and both actor subclasses create or return this
same type.

## NPC

Npc stores one R28 `NpcDefinition` directly. Name/combat/model methods derive from that
definition, and R26 HighlightedNpc stores this exact class.

## Player

Player decodes its appearance from R29 `Stream`, owns equipment/color arrays and
gender/icon/privilege state, plus username/display data and player-specific model assembly.

Exact appearance diagnostics include gender, head icon, skull icon, orb icon, misc icon and
privilege values.

## Acceptance boundary

Chat 2 does not promote R30. Main/Core may accept any desired subset only through an
explicit `semantic_acceptance_spec` bound to
`SEMREVIEW_3283256A87AD65D101B6`.

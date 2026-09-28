# Chat 2 — concrete definition config mappers R347

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R248 already recovered the abstract `rs/t/a` contract as `ConfigDataMapper`.
R347 resolves five concrete definition-mapper implementations whose target type and key
surface are exact in v308.

## Result

- `rs/t/a/a` -> `CLIENT_CLASS_000983` -> `AnimationDefinitionConfigMapper`
- `rs/t/a/b` -> `CLIENT_CLASS_000984` -> `NpcDefinitionConfigMapper`
- `rs/t/a/c` -> `CLIENT_CLASS_000985` -> `SpotAnimationDefinitionConfigMapper`
- `rs/t/a/d` -> `CLIENT_CLASS_000986` -> `ItemDefinitionConfigMapper`
- `rs/t/a/f` -> `CLIENT_CLASS_000988` -> `ObjectDefinitionConfigMapper`
- review: `SEMREVIEW_9EC56F9FC0DE3FB0325F`

## Exact key surfaces

### Animation

The mapper targets `rs/d/a` and exposes animation-definition keys including
`frames`, `frameids`, `durations`, `framestep`, `priority`,
`playeroffhand`, `playermainhand`, `walkprecedence`, `replaymode`,
`animmayaid`, `animmayastart` and `animmayaend`.

Its surviving clone diagnostic explicitly says:

`Could not find clone ID {} for Anim {}`

### NPC

The mapper targets `rs/d/d` and maps `name`, `combatlevel`, `actions`,
`models`, `chatheadmodels`, `standanim`, `walkanim`, rotation animations,
minimap/render flags, pet state, healthbar/hover/glow and related NPC-definition fields.

### Spot animation / GFX

The mapper targets `rs/d/x`. Surviving diagnostics explicitly call the definition
`GFX`; keys include model/modelid, anim/animation, resize, rotation, ambient/contrast,
recolors, retextures and OSRS/OSID metadata.

The project already uses `SpotAnimation` terminology in the legacy loader lane, so the
conservative class name is `SpotAnimationDefinitionConfigMapper`.

### Item

The mapper targets `rs/d/k`; keys cover item name/actions/groundactions, stackability,
notes/templates/certs, model presentation, stack variants, male/female models, recolors,
params and related item-definition state.

### Object

The mapper targets `rs/d/r`; keys cover object name/actions/models, animation, tile
dimensions, resize, contoured-ground state, interaction type/actions, recolors and related
object-definition presentation/state.

## Deliberate holdouts

`rs/t/a/e` and `rs/t/a/g` remain unnamed.

They extend the abstract mapper directly rather than the generic single-definition mapper:

- `e` owns map/land/type/region-style metadata tables;
- `g` loads a special item-ID set with item-definition substitutions/exclusions.

Their mechanics are clear, but their product-domain nouns are not yet precise enough for
R347.

R347 remains non-canonical semantic research only.

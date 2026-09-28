# Chat 2 — exact-v308 Interact Highlight overlay R191

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R191 is a separate non-canonical class-only review for the remaining live overlay in the
already-reviewed Interact Highlight plugin package.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_77D742CC9683DA5877E3`
- field/method proposals: **0**

## Stable ID

`rs/s/i/b` -> `CLIENT_CLASS_000920` -> `InteractHighlightOverlay`

## Existing package authority

Earlier reviews already recover:

- `rs/s/i/a` -> `InteractionHighlightConfig`;
- `rs/s/i/c` -> `InteractHighlightPlugin`.

The exact config options include:

- NPC attack highlight;
- NPC hover highlight;
- NPC interact highlight;
- Object hover highlight;
- Object interact highlight;
- show-on-hover / show-on-interact controls;
- outline colors;
- feather;
- border width.

## Exact plugin ownership

`InteractHighlightPlugin` stores `rs/s/i/b` as its only overlay.

On startup it registers that overlay with the live overlay manager.
On shutdown it clears the overlay's current interaction target and unregisters it.

The plugin's two interaction event handlers do nothing except forward:

- `EntityInteraction`;
- `ObjectInteraction`;

into `rs/s/i/b`.

## Exact overlay behavior

The overlay has two coherent render responsibilities, both inside the reviewed config domain.

### Hover target

During its render pass it inspects the current client menu row.

For an NPC row, when NPC hover highlighting is enabled, it resolves the hovered NPC and
renders that NPC unless it is already the active interaction target.

For an object row, when object hover highlighting is enabled, it resolves the hovered scene
object and renders it unless it is already the active interaction target.

The render calls use the reviewed config's hover colors plus the shared feather/border
settings.

### Active interaction target

The overlay receives an exact `EntityInteraction` or `ObjectInteraction` target.

For NPC interactions it preserves whether the event is combat and uses the corresponding
attack-versus-interact highlight colors. For object interactions it uses the reviewed object
interaction colors.

The highlight fades across the packet/event lifetime, and the overlay clears its target when
the lifetime expires or the player changes location.

No unrelated interface, plugin or gameplay domain is rendered.

## Naming boundary

`InteractHighlightOverlay` is **0.999**.

The name follows the already-reviewed `InteractHighlightPlugin`; the class is exclusively
owned by that plugin and its entire render/event surface implements the exact interaction
highlight configuration.

The readable name is not claimed as an original developer identifier.

R191 remains class-only and non-canonical.

## Acceptance boundary

Chat 2 does not promote R191. Main/Core may accept it only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_77D742CC9683DA5877E3`.

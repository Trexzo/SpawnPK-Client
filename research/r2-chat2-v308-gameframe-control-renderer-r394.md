# Chat 2 — gameframe control renderer R394

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/i/b` -> `CLIENT_CLASS_000297` -> `GameframeControlRenderer`
- proposal: `SEMPROP_F71948D3BE4EF0F787A3`
- review: `SEMREVIEW_0AC29F47A48C06DC0CE8`

## Exact asset ownership

The constructor loads the custom gameframe-control sprite family, including:

- HP / prayer / run / special fills and icons;
- orb backgrounds and drain masks;
- adventure / promo / event orbs;
- hit / experience / heal / refill / boss toggles;
- bank inventory/equipment controls;
- left/right arrows;
- gameframe chat-button and hover-chat sprites.

This is substantially broader than a passive orb-asset holder.

## Live render/layout ownership

Client owns one instance and invokes its render/update methods from the live gameframe path.

R304 `GameHudRenderer` also queries its state to change multiple HUD offsets. Additional
overlay/text systems consult the same gameframe-control state for layout.

## Interaction ownership

Client routes chat-control menu actions into this class with the exact channel constants from
R164 `ChatMessageClassifier`.

The class therefore combines live gameframe control rendering, layout and interaction state.

## Naming boundary

No exact original source class identifier survives. `GameframeControlRenderer` is a
descriptive exact-behavior name chosen to cover both status/orb controls and chat/control-strip
interaction without narrowing the class to one subset.

R394 remains non-canonical semantic research only.

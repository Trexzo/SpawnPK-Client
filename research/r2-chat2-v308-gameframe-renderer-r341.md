# Chat 2 — exact-v308 gameframe renderer R341

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/i/b` -> `CLIENT_CLASS_000297` -> `GameframeRenderer`
- proposal: `SEMPROP_6C64B1168BB0725E8277`
- review: `SEMREVIEW_60BFC0BD95A874A6AB41`

## Exact presentation ownership

The constructor builds the complete gameframe sprite surface, including:

- HP / prayer / run / special-attack orb fills and icons;
- orb drains and active-state variants;
- adventure/event/promo orbs;
- bank inventory/equipment active states;
- chat buttons and hover chat buttons;
- gameframe icon/redstone assets.

The class also owns chat-channel/sidebar presentation state and hover/selected state.

## Rendering behavior

The class directly renders `rs/l/F` sprites throughout its methods.

Its render paths cover:

- gameframe orb state;
- chat-channel buttons;
- active/hover variants;
- sidebar/gameframe state;
- orb drain/fill presentation;
- Graphics2D-backed orb rendering.

## Independent consumer joins

`Client` invokes this class during the main frame lifecycle and mutates presentation state
through it.

The central R303/R305-era render path `rs/l/b/b` repeatedly queries its state to adjust
HUD/overlay geometry.

Other overlay/UI consumers also query its state when positioning themselves against the
active gameframe.

## Existing semantic boundaries

- R8 `GameframeNavigationInterface` is a separate widget/interface navigation builder.
- R334 `GameframeSidebarTab` is this class's nested tab enum.

The outer class is therefore the concrete gameframe presentation renderer, not either of
those already-reviewed roles.

R341 remains non-canonical semantic research only.

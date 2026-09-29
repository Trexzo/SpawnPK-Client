# Chat 2 — Donation Shopping Cart interface R376

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/n/c/aw` -> `CLIENT_CLASS_000627` -> `DonationShoppingCartInterface`
- proposal: `SEMPROP_44D6A25447470D416C3C`
- review: `SEMREVIEW_F44CA4AD45209B25930B`

## Exact interface identity

The class builds root widget **60200** and preserves:

- `@or1@Donation Shopping Cart`
- `@or1@Subtotal: @yel@$0.00`
- `Checkout`
- `Checkout @yel@($0.00)`
- `Purchase Options`
- `Shopping Cart`
- `misc/cart 0`
- `misc/cart 1`

## Existing protocol join

R128 already recovered:

- `DonationShoppingCartParticleOverlayPacketHandler`
- `DonationShoppingCartParticleOverlay`
- `DonationShoppingCartParticleStyle`

The R128 handler is registered from the static handler field owned by `rs/n/c/aw`.
Its selectors update the cart's particle/progress presentation state only.

R376 therefore completes the self-identifying root interface for that already-reviewed
subsystem.

## Boundary

No payment/business logic is inferred from the interface. R376 remains non-canonical
class-only semantic research.

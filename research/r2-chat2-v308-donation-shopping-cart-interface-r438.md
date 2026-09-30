# Chat 2 — exact-v308 Donation Shopping Cart interface R438

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/n/c/aw` -> `CLIENT_CLASS_000627` -> `DonationShoppingCartInterface`
- proposal: `SEMPROP_44D6A25447470D416C3C`
- review: `SEMREVIEW_F44CA4AD45209B25930B`

## Exact screen identity

The builder extends R436 `CustomInterfaceBuilder` and creates root widget **60200**.

Its own exact title is:

`@or1@Donation Shopping Cart`

The primary root background uses:

`misc/cart 0`

## Exact checkout/purchase presentation

The interface constructs client presentation for:

- Daily Offer
- Exclusive Offers
- Shopping Cart
- subtotal text
- Empty
- Checkout
- PayPal (Card / Bank)
- OSRS GP
- purchase-option and checkout button variants

It also contains exact promotional strings and cart-state widgets under the 600xx/602xx
widget ranges.

## Reverse references

Outside the builder itself, exact v308 references `rs/n/c/aw` only from:

- R436 `CustomInterfaceRegistry`
- `rs/q/a/a/b`

No unrelated interface family owns this builder.

## Boundary

This recovery is presentation-only. The interface does not prove payment processing,
purchase fulfilment, pricing authority or any server-side commerce implementation.

R438 remains non-canonical semantic research only.

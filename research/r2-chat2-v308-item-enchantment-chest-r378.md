# Chat 2 — Item Enchantment Chest interface R378

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/n/c/G` -> `CLIENT_CLASS_000552` -> `ItemEnchantmentChestInterface`
- proposal: `SEMPROP_114D9AB3EE0D8EC99ED4`
- review: `SEMREVIEW_D871A22E019AF4565E43`

## Exact identity

The class builds root widget **31244** and preserves the literal title:

`@or1@Item Enchantment Chest`

Its exact interface vocabulary includes:

- Enchantments
- Item name
- Categories
- Enchant
- Attempt Enchantment
- Success chance
- Ingredients (cost to attempt)
- Select a category
- Select enchantment
- Select item
- Search by name
- Search item

It also owns the live result animation/presentation with:

- `Preparing enchantment..`
- `<img=24> @dgr@Success! Congratulations! <img=24>`
- `@bla@Enchantment failed!`

and the matching fountain sprite state.

## Boundary

The name reflects the exact visible title and complete widget responsibility. It does not
infer enchantment odds, costs or server-side acceptance rules.

R378 remains non-canonical class-only semantic research.

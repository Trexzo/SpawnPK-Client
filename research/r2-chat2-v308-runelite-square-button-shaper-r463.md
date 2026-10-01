# Chat 2 — exact-v308 RuneLiteSkin square button shaper R463

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Corrected result

`rs/gui/c` -> `CLIENT_CLASS_000203` -> `RuneLiteSkinSquareButtonShaper`

- proposal: `SEMPROP_EB85CBF47EB4C5D8A116`
- review: `SEMREVIEW_8C570CBA1E780914BF90`

## Why the R463 name changed

The first R463 attempt used `RuneLiteSquareButtonShaper`.

That collided with R177, which already owns a **different exact-v308 class**:

- R177: `rs/ui/c/b` / `CLIENT_CLASS_001034` -> `RuneLiteSquareButtonShaper`

R463 instead targets:

- `rs/gui/c` / `CLIENT_CLASS_000203`

R22 fixes its parent family as:

- `rs/gui/a` -> `RuneLiteLookAndFeel`
- `rs/gui/b` -> `RuneLiteSkin`

The corrected name therefore qualifies the exact parent family rather than pretending the
two shaper implementations are one class.

## Exact role

R22 `RuneLiteSkin` constructs exactly one `rs/gui/c` and assigns it to its inherited
`buttonShaper` field.

The helper extends Substance `ClassicButtonShaper` and overrides only:

`getCornerRadius(AbstractButton, float)`

The result is always:

`0.0f`

So its exact behavior is to make the R22 RuneLiteSkin family's Substance buttons
square-cornered.

## Boundary

R463 remains non-canonical semantic research only. No source-name identity beyond the
descriptive family-qualified role is claimed.

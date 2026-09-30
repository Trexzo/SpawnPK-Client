# Chat 2 — exact-v308 Sprite resource registry R384

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/l/I` -> `CLIENT_CLASS_000358` -> `SpriteResourceRegistry`
- proposal: `SEMPROP_CB28D68887091E0D6D07`
- review: `SEMREVIEW_7CD1A67D202DACB89B3E`

## Registration contract

R55 already fixes `rs/l/F` as `Sprite`.

The String factory in `rs/l/I` creates a blank Sprite, stores the supplied resource path
on that Sprite, appends it to one global Sprite list and returns the registered object.

The boolean overload follows the same registry path; the boolean does not acquire a stronger
independent semantic role in this class.

## Startup materialization

The no-arg static method traverses all registered Sprites and materializes each path-backed
resource:

- loads the AWT Image from the Sprite resource base + stored path;
- reads icon width/height;
- resets Sprite dimension/offset state;
- allocates width*height pixel storage;
- fills the pixels with PixelGrabber;
- applies the existing Sprite color-key cleanup path when required.

Client calls this exact materialization pass during shared asset startup.

## Exact consumers

R308 `CombatHudSpriteAssets` registers exact paths through this registry, including:

- `misc/singlesplus`
- `misc/singlesplushot`
- `popups/hp 0` through `popups/hp 3`
- `hitmarks/old/poise`
- `popups/scope`

This fixes the class as a path-backed Sprite resource registry/materializer rather than a
generic image cache.

## Boundary

The proposed name is descriptive exact-v308 behavior only and does not claim a lost original
developer identifier.

R384 remains non-canonical class-only semantic research.

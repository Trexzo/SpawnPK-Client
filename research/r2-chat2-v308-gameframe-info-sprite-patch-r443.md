# Chat 2 — exact-v308 gameframe info sprite patch R443

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/n/c/aV` -> `CLIENT_CLASS_000597` -> `GameframeInfoSpritePatch`
- proposal: `SEMPROP_A601147114C5A7C91846`
- review: `SEMREVIEW_23C60DC21FD9C3C0E959`

## Stable identity

The canonical class sequence is directly bracketed by already-reviewed exact-v308 owners:

- `rs/n/c/aU` -> `CLIENT_CLASS_000596`
- `rs/n/c/aV` -> `CLIENT_CLASS_000597`
- `rs/n/c/aW` -> `CLIENT_CLASS_000598`
- `rs/n/c/aX` -> `CLIENT_CLASS_000599`
- `rs/n/c/aY` -> `CLIENT_CLASS_000600`
- `rs/n/c/aZ` -> `CLIENT_CLASS_000601`

## Exact behavior

The class extends R436 `CustomInterfaceBuilder` but does not construct an independent root
screen.

Its build method patches three pre-existing widgets:

- widget **29998** gets child **65747** using `gameframe/info/sprite 2`;
- widget **29997** gets child **65746** using `gameframe/info/sprite 3`;
- widget **29994** gets child **65745** using `gameframe/info/sprite 4`.

Each child is placed at exactly:

- x = **18**
- y = **12**

R436 `CustomInterfaceRegistry` constructs this builder in the live exact-v308 custom
interface catalogue.

## Naming boundary

No surviving literal or independent consumer proves a narrower screen or gameplay noun for
widgets 29994/29997/29998.

`GameframeInfoSpritePatch` therefore describes only the exact observable behavior and
resource namespace. It is not claimed as an original stripped developer identifier.

R443 remains non-canonical semantic research only.

# Chat 2 — exact-v308 custom interface builder architecture R436

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/n/c` -> `CLIENT_CLASS_000544` -> `CustomInterfaceBuilder`
- `rs/n/d` -> `CLIENT_CLASS_000680` -> `CustomInterfaceRegistry`
- review: `SEMREVIEW_B1A00DE57E48E73FF05B`

## Builder base

R56 already fixes `rs/n/e` as `RSInterface`.

`rs/n/c` extends that class and provides the common base used by the large SpawnPK
custom-interface family. It stores the shared classic font array and requires concrete
subclasses to implement a no-argument construction method.

Its remaining base methods are optional/default lifecycle or update hooks.

## Registry/composition root

`rs/n/d` owns:

- `List<rs/n/c>` — the custom-interface builder catalogue;
- the shared font array used to instantiate those builders.

During interface initialization it clears the catalogue and explicitly constructs/registers
the concrete custom-interface classes. The exact list includes many classes already recovered
individually by Chat 2, spanning raids, Blood Fountain, Blood Diamond Fuser, Trading Post,
mailbox, confirmation, construction and many other SpawnPK-specific screens.

This establishes `rs/n/d` as the custom-interface composition/registry layer rather than
another individual interface definition.

## Boundary

Names describe exact architecture and do not imply canonical acceptance or source rewrite.

R436 remains non-canonical semantic research only.

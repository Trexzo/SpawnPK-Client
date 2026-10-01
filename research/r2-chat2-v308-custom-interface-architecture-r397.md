# Chat 2 — custom interface construction architecture R397

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/n/c` -> `CLIENT_CLASS_000544` -> `CustomInterfaceBuilder`
- `rs/n/d` -> `CLIENT_CLASS_000680` -> `CustomInterfaceBootstrap`
- review: `SEMREVIEW_D509A467C29613ACA64E`

## CustomInterfaceBuilder

R56 already fixes `rs/n/e` as `RSInterface`, the widget/interface definition object.

Direct `rs/n/c` is the abstract code-builder layer above that widget model. It:

- extends RSInterface;
- owns the shared TextDrawingArea[] font table;
- defines one required abstract build hook;
- provides optional update/reset hooks;
- exposes a boolean retain/enabled predicate.

The exact-v308 `rs/n/c/*` catalogue contains more than one hundred concrete builders that
inherit this contract.

## CustomInterfaceBootstrap

Direct `rs/n/d` owns the catalogue bootstrap.

Its static initialization path:

1. clears the retained builder list;
2. stores the shared font table;
3. constructs the concrete custom-interface builders in deterministic order;
4. invokes each builder's build hook;
5. retains only builders whose predicate says they remain active;
6. finalizes the shared RSInterface/font setup.

It is referenced directly by Client and live interface code.

## Boundary

This pair is distinct from the R284 interface-layout manager family under `rs/n/d/*`.
Direct `rs/n/d` is the custom-interface catalogue bootstrap, while `rs/n/d/c` is one
per-interface layout manager.

R397 remains non-canonical semantic research only.

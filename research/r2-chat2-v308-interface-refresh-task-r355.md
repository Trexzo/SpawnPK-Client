# Chat 2 — exact-v308 interface refresh task R355

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/n/b/a/a` -> `CLIENT_CLASS_000539` -> `InterfaceRefreshTask`
- proposal: `SEMPROP_735A6B7405E3ADE4F26A`
- review: `SEMREVIEW_F59F018F7EF8E470171F`

## Exact hierarchy

R287 already fixes:

- `rs/n/b/a` -> `TimedInterfaceTask`
- `rs/n/b/b` -> `InterfaceTaskRegistry`

R288 separately fixes:

- `rs/n/b/a/c` -> `DeferredHoverTask`
- `rs/n/b/a/d` -> `InterfaceRenderTask`

The remaining direct subtype `rs/n/b/a/a` adds no hover/deferred/render-specific state.
Its constructor only forwards the supplied interval to the TimedInterfaceTask base.

## Dedicated registry

TimedInterfaceTask owns a separate int-keyed registry specifically typed to this subtype.
It is distinct from the DeferredHoverTask and InterfaceRenderTask registries.

## Concrete consumer

The only exact-v308 concrete subtype found is R285
`EventActivityViewerRefreshTask`.

EventActivityViewerInterface registers it against interface **30072** with a **500 ms**
interval.

Its task body walks the activity model list and rewrites the corresponding text widgets
starting at widget 30333.

That fixes the subclass family as periodic interface refresh/update work.

## Boundary

The proposed name is `InterfaceRefreshTask`, not a generic scheduler name and not a
render-task alias. Exact v308 exposes only one concrete consumer.

R355 remains non-canonical semantic research only.

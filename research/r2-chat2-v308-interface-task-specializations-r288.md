# Chat 2 — exact-v308 interface task specializations R288

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic result

- `rs/n/b/a/b` -> `CLIENT_CLASS_000540` -> `InterfaceDrawCallback`
- `rs/n/b/a/c` -> `CLIENT_CLASS_000541` -> `DeferredHoverTask`
- `rs/n/b/a/d` -> `CLIENT_CLASS_000542` -> `InterfaceRenderTask`
- review: `SEMREVIEW_03D4A9B99AFBE803214A`
- unresolved: **0**
- member proposals: **0**

## Exact-v308 execution phases

`InterfaceDrawCallback` preserves the exact method name/signature `draw(int, int)`. `RSInterface` owns two fields of this type, and the interface renderer invokes those callbacks with resolved widget x/y coordinates at two draw phases.

`DeferredHoverTask` is dispatched only from Client hover hit-testing. Its inherited timed hook queues the task into a static set rather than performing the effect immediately. Client later flushes that set through the subtype's concrete `e()` method after interface traversal. The retained hotspot tooltip tasks are exact consumers of this phase.

`InterfaceRenderTask` is dispatched by widget/interface id from the main interface renderer immediately before the widget's own render/update hooks. The retained Event Brawl status task is registered in this registry under interface id 40087 with a 1000 ms interval.

## Deliberate exclusion

`rs/n/b/a/a` remains unnamed. It is clearly another TimedInterfaceTask subtype and EventActivityViewerRefreshTask extends it, but its exact dispatch phase is not as directly evidenced as the three roles retained here.

## Boundary

R288 is non-canonical semantic research only. No acceptance, source rewrite or source materialization is performed.

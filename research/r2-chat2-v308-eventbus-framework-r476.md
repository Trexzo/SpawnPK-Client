# Chat 2 — exact-v308 event bus framework R476

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/eventbus/DeferredEventBus` -> `CLIENT_CLASS_000160` -> `DeferredEventBus`
- `rs/eventbus/EventBus` -> `CLIENT_CLASS_000161` -> `EventBus`
- `rs/eventbus/Subscribe` -> `CLIENT_CLASS_000162` -> `Subscribe`
- review: `SEMREVIEW_FEA4928AD76FD17E07CE`

These identities are unusually strong because the recovered source filenames already preserve
the unobfuscated class names and exact bytecode independently matches those contracts.

## EventBus

The live bus scans object methods for `@Subscribe`, validates subscriber signatures,
constructs priority-bearing subscriber bindings, supports direct typed Consumer registration,
unregisters by owner or binding and dispatches posted events with exception handling.

Exact diagnostics include invalid @Subscribed method conditions and subscriber invocation
errors.

## DeferredEventBus

The deferred bus extends EventBus but wraps an injected live EventBus:

- register/unregister delegate immediately to the live bus;
- post enqueues into a ConcurrentLinkedQueue;
- replay snapshots queue size, polls those pending events and forwards them to the live bus.

This is the exact deferred-posting bridge bound under the named Deferred EventBus application
binding recovered in R321.

## Subscribe

Runtime, documented METHOD annotation with exactly:

`float priority() default 0.0f`

EventBus.register reads that priority directly.

## Boundary

R476 is class-only non-canonical semantic research.

# Chat 2 — exact-v308 event bus infrastructure R168

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R168 is a separate non-canonical class-only review for the exact-name event bus
infrastructure that survives unobfuscated in v308.

## Deterministic review result

- candidate classes: **4**
- resolved proposals: **4**
- unresolved: **0**
- review ID: `SEMREVIEW_0207EC3E587BBD212B82`
- field/method proposals: **0**

## Stable IDs

- `rs/eventbus/DeferredEventBus` -> `CLIENT_CLASS_000162` -> `DeferredEventBus`
- `rs/eventbus/EventBus` -> `CLIENT_CLASS_000163` -> `EventBus`
- `rs/eventbus/EventBus$Subscriber` -> `CLIENT_CLASS_000164` -> `EventBusSubscriber`
- `rs/eventbus/Subscribe` -> `CLIENT_CLASS_000165` -> `Subscribe`

## Exact-name boundary

Three class names survive verbatim in the exact client:

- `DeferredEventBus`;
- `EventBus`;
- `Subscribe`.

The nested record survives as `EventBus$Subscriber`; R168 uses
`EventBusSubscriber` only to express that exact nested identity as one top-level Java
identifier for semantic-remap tooling.

## EventBus

`EventBus.register(Object)` scans declared methods for the exact runtime
`@Subscribe` annotation.

Registration validates that each subscriber method:

- returns void;
- has exactly one parameter;
- is non-static;
- receives a non-primitive event class.

The resulting subscriber records are sorted by descending float priority and then by
subscriber class name.

`post(Object)` dispatches by the event object's exact runtime class and invokes each
subscriber. Subscriber exceptions are routed through the configured exception consumer;
the default path logs:

`Uncaught exception in event subscriber`

The class also supports unregistering either all handlers belonging to one object or one
specific subscriber record.

## EventBusSubscriber

The nested record stores:

- subscriber object;
- reflective Method;
- float priority;
- optional `Consumer<Object>` lambda.

Invocation uses the lambda when present, otherwise the reflective Method.

## Subscribe

The exact annotation is:

- runtime retained;
- targeted at methods;
- documented;
- one `float priority()` element;
- default priority **0.0**.

This is the exact annotation consumed by EventBus registration.

## DeferredEventBus

The class extends `EventBus` but delegates registration to one backing EventBus.

Its `post(Object)` queues events into a `ConcurrentLinkedQueue`.

`replay()` snapshots the current queue size, polls that many pending events and posts each
one into the backing EventBus. Events added during replay are therefore deferred to a later
replay pass.

## Live-use evidence

Exact class-reference scanning finds:

- `EventBus` referenced by `Client` plus UI, plugin, overlay, networking and runtime
  classes;
- `Subscribe` referenced across numerous subsystem listener classes;
- `DeferredEventBus` wired through the runtime/injection layer.

This is live client infrastructure rather than an isolated utility package.

## Acceptance boundary

R168 remains non-canonical. Main/Core may accept any proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_0207EC3E587BBD212B82`.

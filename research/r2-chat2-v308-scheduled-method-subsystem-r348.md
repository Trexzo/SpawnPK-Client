# Chat 2 — exact-v308 scheduled method subsystem R348

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/y/a` -> `CLIENT_CLASS_001122` -> `ScheduledTask`
- `rs/y/b` -> `CLIENT_CLASS_001123` -> `ScheduledMethod`
- `rs/y/c` -> `CLIENT_CLASS_001124` -> `ScheduledMethodScheduler`
- review: `SEMREVIEW_087D5FEB2E6D2FE0F120`

## ScheduledTask annotation

`rs/y/a` is a runtime-visible Java annotation targeted exclusively at methods.

Its exact contract is:

- one `long` interval;
- one `ChronoUnit`;
- one boolean execution-mode flag, default `false`.

The live plugin/service scanner calls `Method.getAnnotation(rs/y/a.class)` for every public
method and creates a scheduler record whenever the annotation is present.

## ScheduledMethod

The semantic noun survives directly in exact bytecode. Its `toString()` format is:

`ScheduledMethod(schedule=..., method=..., object=..., lambda=..., last=...)`

State consists exactly of:

- schedule annotation;
- reflected Method;
- owner object;
- optional Runnable lambda generated through LambdaMetafactory;
- last-trigger Instant.

The scanner logs `Scheduled task {}`, registers the record, and removes records belonging
to an unloaded plugin/service.

## ScheduledMethodScheduler

`rs/y/c` is a singleton application service.

It owns:

- injected `ScheduledExecutorService`;
- `CopyOnWriteArrayList<ScheduledMethod>`.

For each registered record it computes:

`Duration.between(last, now)`

and compares it with:

`Duration.of(interval, ChronoUnit)`.

When due it:

1. logs `Scheduled task triggered: {}`;
2. updates the last-trigger Instant;
3. either submits execution to the executor or invokes inline according to the annotation
   boolean;
4. handles reflection/task failures through explicit warning paths.

R321's ClientApplicationModule binds this scheduler in the root Guice graph.

## Boundary

R348 is class-only semantic research. Annotation member names are not proposed here.

No original stripped developer identifier is claimed except the exact preserved
`ScheduledMethod` noun corroborated by the class's own string representation.

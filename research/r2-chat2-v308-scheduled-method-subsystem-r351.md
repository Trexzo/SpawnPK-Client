# Chat 2 — scheduled-method subsystem R351

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/y/a` -> `CLIENT_CLASS_001122` -> `ScheduledMethodAnnotation`
- `rs/y/b` -> `CLIENT_CLASS_001123` -> `ScheduledMethod`
- `rs/y/c` -> `CLIENT_CLASS_001124` -> `ScheduledMethodScheduler`
- review: `SEMREVIEW_5746D4B983CB42373512`

Stable IDs were verified against the global sorted exact-v308 class lineage:

- `rs/y` -> 001121
- `rs/y/a` -> 001122
- `rs/y/b` -> 001123
- `rs/y/c` -> 001124
- `rs/z` -> 001125
- R252 already fixes `rs/z/a` -> 001126.

## ScheduledMethodAnnotation

`rs/y/a` is a runtime-retained Java annotation targeted specifically at methods.

It exposes:

- one long interval;
- one `ChronoUnit`;
- one boolean execution flag, default `false`.

The live plugin manager scans plugin methods with `getAnnotation(rs/y/a.class)`.

## ScheduledMethod

`rs/y/b` retains unusually strong original semantics through its own exact toString:

`ScheduledMethod(schedule=..., method=..., object=..., lambda=..., last=...)`

Its state exactly matches that text:

- schedule annotation;
- reflected Method;
- target object;
- bound Runnable lambda;
- last-run Instant.

Construction initializes last-run to `Instant.now()`.

## ScheduledMethodScheduler

`rs/y/c` is a singleton scheduler containing:

- `CopyOnWriteArrayList<rs/y/b>`;
- injected `ScheduledExecutorService`;
- logger.

Its tick lifecycle:

1. capture `Instant.now()`;
2. compute `Duration.between(lastRun, now)`;
3. construct configured duration from annotation interval + ChronoUnit;
4. trigger when elapsed reaches/exceeds that duration;
5. log `Scheduled task triggered: {}`;
6. update last-run;
7. either submit the Runnable to the executor or invoke inline depending on the annotation boolean.

The plugin manager registers scheduled methods when scanning plugin instances and removes
all records belonging to an object when that plugin is unloaded.

## Boundary

These names describe exact runtime architecture and do not infer any plugin-specific task
semantics.

R351 remains non-canonical semantic research only.

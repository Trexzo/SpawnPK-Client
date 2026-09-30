# Chat 2 — exact-v308 RuneLite scheduler identities R426

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/y/a` -> `CLIENT_CLASS_001122` -> `Schedule`
- `rs/y/b` -> `CLIENT_CLASS_001123` -> `ScheduledMethod`
- `rs/y/c` -> `CLIENT_CLASS_001124` -> `Scheduler`
- review: `SEMREVIEW_0C940EC4C68D5DDC6CF0`

## Exact source continuity

The surviving scheduler implementation is structurally and textually identical to the
RuneLite task scheduler family.

### Schedule

The annotation exposes:

- a long scheduling period;
- `ChronoUnit`;
- asynchronous boolean.

### ScheduledMethod

The record stores:

- Schedule metadata;
- reflected Method;
- target Object;
- optional Runnable;
- last-run Instant.

### Scheduler

The scheduler owns a CopyOnWriteArrayList of ScheduledMethod records and an injected
ScheduledExecutorService. On each scheduling pass it compares elapsed time against the
configured duration, logs:

`Scheduled task triggered: {}`

then updates last-run state and invokes synchronously or through the executor.

The surviving warning strings also match the upstream source:

- `error invoking scheduled task`
- `error during scheduled task`

## Boundary

The root `rs/y` class is unrelated legacy animation-config override code and is deliberately
not folded into this scheduler batch.

R426 remains non-canonical Chat 2 semantic research only.

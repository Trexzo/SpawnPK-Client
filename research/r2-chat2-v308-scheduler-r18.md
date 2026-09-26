# Chat 2 — exact-v308 scheduler semantics R18

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R18 is a separate non-canonical class-only semantic review batch. It does not alter
Main/Core's accepted R2 semantic authority or prior R3-R17 review batches.

## Deterministic review result

- candidate classes: **3**
- resolved proposals: **3**
- unresolved: **0**
- review ID: `SEMREVIEW_5F86889B10D97E6837BE`
- field/method proposals: **0**

## Scheduling framework

- `rs/y/a` -> `Schedule`
- `rs/y/b` -> `ScheduledMethod`
- `rs/y/c` -> `Scheduler`

`Schedule` is a runtime METHOD annotation carrying a long interval, ChronoUnit and boolean
execution flag.

`ScheduledMethod` is directly self-identifying in exact-v308 bytecode:

`ScheduledMethod(schedule=…, method=…, object=…, lambda=…, last=…)`

Its fields match that text exactly: Schedule annotation, reflected Method, target object,
Runnable lambda and last execution Instant.

`Scheduler` is a singleton service owning a ScheduledExecutorService plus a
`List<ScheduledMethod>`. Exact diagnostics include:

- `Scheduled task triggered: {}`
- `error during scheduled task`
- `error invoking scheduled task`

It registers/removes scheduled methods and executes them according to their Schedule
metadata.

## Acceptance boundary

Chat 2 does not promote R18. Main/Core may accept any desired subset only through an
explicit `semantic_acceptance_spec` bound to
`SEMREVIEW_5F86889B10D97E6837BE`.

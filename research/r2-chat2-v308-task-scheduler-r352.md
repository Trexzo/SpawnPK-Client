# Chat 2 — RuneLite task scheduler source identity R352

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/y/a` -> `CLIENT_CLASS_001122` -> `Schedule`
- `rs/y/b` -> `CLIENT_CLASS_001123` -> `ScheduledMethod`
- `rs/y/c` -> `CLIENT_CLASS_001124` -> `Scheduler`
- review: `SEMREVIEW_0C940EC4C68D5DDC6CF0`

## Stable-ID boundary

The canonical exact-v308 class sequence around this family is independently anchored by
earlier reviewed classes:

- `rs/x` -> 001114;
- `rs/x/a` -> 001115;
- `rs/x/b` -> 001116;
- `rs/x/e` -> 001119;
- `rs/x/f` -> 001120;
- `rs/y` -> 001121;
- `rs/y/a` -> 001122;
- `rs/y/b` -> 001123;
- `rs/y/c` -> 001124;
- `rs/z` -> 001125;
- `rs/z/a` -> 001126;
- `rs/z/b` -> 001127.

The top-level `rs/y` class itself is unrelated legacy animation-config parsing and is not
part of the task scheduler family.

## Schedule

`rs/y/a` is a runtime-retained method annotation with:

- a long interval;
- a `ChronoUnit`;
- a boolean flag defaulting false.

The live plugin scan path reads the annotation from methods and turns annotated methods into
scheduled records.

## ScheduledMethod

`rs/y/b` stores:

- Schedule;
- reflected Method;
- target Object;
- optional Runnable lambda;
- last-run Instant.

Its exact-v308 string-concat recipe preserves the literal identity:

`ScheduledMethod(schedule=..., method=..., object=..., lambda=..., last=...)`

This directly exposes the historical class noun.

## Scheduler

`rs/y/c` is a singleton scheduler with an injected `ScheduledExecutorService` and
`CopyOnWriteArrayList<ScheduledMethod>`.

Each tick:

1. computes time since the record's last Instant;
2. converts the Schedule interval + ChronoUnit into a Duration;
3. triggers due methods;
4. updates last-run time;
5. executes asynchronously through the executor when requested, otherwise synchronously;
6. invokes either the prebuilt Runnable lambda or reflected Method.

Surviving exact-v308 logs include:

- `Scheduled task triggered: {}`
- `error invoking scheduled task`
- `error during scheduled task`

## Historical source corroboration

Current public RuneLite history contains `net.runelite.client.task.Schedule` and
`Scheduler` with the same architecture and the exact `Scheduled task triggered: {}`
log text. This historical source evidence corroborates, but does not override, exact-v308
bytecode.

R352 remains non-canonical Chat 2 research only.

# Chat 2 — exact-v308 exception-logging executor utilities R468

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Result

- `rs/A/e` -> `CLIENT_CLASS_000008` -> `CallableExceptionLogger`
- `rs/A/h` -> `CLIENT_CLASS_000011` -> `ExecutorServiceExceptionLogger`
- review: `SEMREVIEW_ECC57D4256D112A82094`

## CallableExceptionLogger

Exact v308 implements `Callable<V>`, stores one wrapped Callable and delegates `call()`.
Any Throwable is logged with:

`Uncaught exception in callable {}`

and rethrown.

The class also exposes the same static generic wrapper factory as RuneLite
`net.runelite.client.util.CallableExceptionLogger`.

## ExecutorServiceExceptionLogger

Exact v308 implements the complete `ScheduledExecutorService` contract over one wrapped
scheduled executor.

Task-taking methods wrap work before delegation:

- Runnable -> R467 `RunnableExceptionLogger`
- Callable -> `CallableExceptionLogger`

This covers submit, execute, schedule, fixed-rate and fixed-delay paths. Lifecycle/query and
bulk invocation methods delegate to the underlying service.

That matches RuneLite
`net.runelite.client.util.ExecutorServiceExceptionLogger`.

## Boundary

R468 is non-canonical semantic research only.

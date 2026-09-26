# Chat 2 — exact-v308 client clock family R176

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R176 is a separate non-canonical class-only review for the exact client main-loop clock
abstraction, its millisecond/nanosecond implementations and their shared sleep helper.

## Deterministic review result

- candidate classes: **4**
- resolved proposals: **4**
- unresolved: **0**
- review ID: `SEMREVIEW_A4302A7164027FE8DF30`
- field/method proposals: **0**

## Stable IDs

- `rs/g/b` -> `CLIENT_CLASS_000179` -> `ClientClock`
- `rs/g/c` -> `CLIENT_CLASS_000180` -> `MillisClientClock`
- `rs/g/d` -> `CLIENT_CLASS_000181` -> `NanoClientClock`
- `rs/g/e` -> `CLIENT_CLASS_000182` -> `SleepUtil`

## ClientClock

`rs/g/b` is abstract and exposes exactly two runtime operations:

- reset the clock;
- wait/advance from a target cycle duration and minimum sleep value, returning an integer
  count of client logic cycles to execute.

The base client `rs/C` stores this type as the main-loop clock.

Its exact loop calls the clock, runs the returned number of logic cycles and then renders.

## Exact clock factory

`rs/C.be()` is the factory:

1. construct `rs/g/d`;
2. return it if construction succeeds;
3. catch any `Throwable`;
4. construct and return `rs/g/c`.

That directly establishes one primary nanosecond clock and one millisecond fallback clock.

## MillisClientClock

`rs/g/c` uses `System.currentTimeMillis()`.

It wraps that source with a synchronized monotonic correction so backwards wall-clock jumps
are compensated rather than returned directly.

The instance keeps a ten-entry timestamp ring and computes:

- a bounded fixed-point cycle rate;
- a minimum sleep delay;
- a 0..255 cycle accumulator;
- the number of client cycles that should run after each wait.

It delegates sleeping to `SleepUtil`.

## NanoClientClock

`rs/g/d` initializes and resets from:

`System.nanoTime()`

Its wait path converts the requested client cycle duration to nanoseconds, sleeps until the
scheduled timestamp, advances the next timestamp in exact cycle-sized steps and returns the
number of catch-up cycles.

Catch-up is capped at **10** cycles.

A live-client mode branch uses `Launcher.n().o()`, `Client.au()` and `Client.cc`, but
the class remains entirely nanosecond scheduling/timing.

## SleepUtil

`rs/g/e` has one public static sleep responsibility.

For positive millisecond delays divisible by 10 it performs:

- `Thread.sleep(delay - 1)`;
- then `Thread.sleep(1)`.

For other positive delays it performs one `Thread.sleep(delay)`.

Both clock implementations consume this helper and no unrelated exact-v308 responsibility
was found.

## Naming boundary

`ClientClock`, `MillisClientClock` and `NanoClientClock` are **0.999** because the
abstract contract, exact time sources and factory selection all agree.

`SleepUtil` is **0.998** because the behavior is exact but the original utility noun was
stripped.

R176 remains class-only.

## Acceptance boundary

Chat 2 does not promote R176. Main/Core may accept any subset only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_A4302A7164027FE8DF30`.

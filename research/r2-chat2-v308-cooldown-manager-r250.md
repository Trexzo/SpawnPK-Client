# Chat 2 — exact-v308 CooldownManager R250

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic review result

- `rs/z/d` -> `CLIENT_CLASS_001129` -> `CooldownManager`
- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_ADDD4EB99544180F621D`
- field/method proposals: **0**

## Exact timer-registry behavior

Exact v308 `rs/z/d` owns a `Map<String, rs.z.b>`.

For a caller-supplied key and duration it:

- refuses to start when the keyed timer is still active;
- otherwise creates `rs/z/a(duration)`, starts it and stores it under the key;
- can force a restart by removing then starting;
- reports whether a keyed timer is active;
- reports remaining milliseconds;
- removes one timer;
- clears all timers;
- exposes the timer registry.

`rs/z/a` itself stores start time + duration and computes active/remaining time with `System.currentTimeMillis()`.

## Independent exact consumers

### Login throttle

Both `rs/Client` and `rs/l/d/c` call:

`Launcher.f().a("LOGIN_COOLDOWN", 500L)`

and proceed with the login attempt only when the keyed 500 ms cooldown can be acquired.

### Tray-notification throttle

`rs/gui/Launcher` constructs one `rs/z/d` and, before `TrayIcon.displayMessage`, calls the same acquire operation with:

- notification title as the key;
- duration **5000 ms**.

This establishes a shared keyed cooldown registry rather than a login-specific timer.

## Naming boundary

`CooldownManager` is a conservative semantic recovery name supported by two independent runtime consumers. It does not claim a verbatim original developer identifier.

The adjacent timer base/interface classes remain deliberately unnamed in R250 because their individual semantic nouns are weaker than the manager identity.

## Acceptance boundary

R250 remains class-only and non-canonical. Chat 2 performs no semantic acceptance.

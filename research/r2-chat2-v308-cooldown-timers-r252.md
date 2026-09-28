# Chat 2 — exact-v308 cooldown timer family R252

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic review result

- `rs/z/a` -> `CLIENT_CLASS_001126` -> `DurationCooldownTimer`
- `rs/z/b` -> `CLIENT_CLASS_001127` -> `CooldownTimer`
- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_D44A1230F5958BBDE2FB`
- field/method proposals: **0**

## Exact stable IDs

The exact v308 JAR was re-indexed using the canonical `seed_lineage()` rule: every `rs/**.class` internal name is sorted lexicographically and assigned a 1-based ordinal.

The exact tail is:

- `rs/z/a` -> `CLIENT_CLASS_001126`
- `rs/z/b` -> `CLIENT_CLASS_001127`
- `rs/z/c` -> `CLIENT_CLASS_001128`
- `rs/z/d` -> `CLIENT_CLASS_001129`

The JAR contains **1,129** `rs/**` classes. These IDs are derived from the complete baseline ordering, not package adjacency.

## Exact timer behavior

### `rs/z/b`

This is an abstract class with the contract:

- `void a()` — start/reset
- `boolean b()` — active state
- `long c()` — remaining milliseconds

R250 `CooldownManager` stores `Map<String, rs.z.b>` and calls the latter two methods through this base type.

### `rs/z/a`

This is the only concrete timer implementation in the package.

It stores two longs:

- start timestamp;
- configured duration.

Its constructor receives the duration. Starting records `System.currentTimeMillis()`. Active state is true while elapsed time is below duration. Remaining time returns zero when inactive, otherwise duration minus elapsed time.

R250 constructs this exact class for keyed login and tray-notification cooldowns.

## Deliberately unresolved

`rs/z/c` remains unnamed.

It is a one-method boolean interface referenced only by a protected field on `rs/z/b`, and no exact-v308 behavioral consumer establishes a precise semantic noun. R252 does not name dead/weakly evidenced interfaces from shape alone.

## Naming boundary

`CooldownTimer` and `DurationCooldownTimer` are descriptive recovery names, not claims of verbatim original source identifiers.

## Acceptance boundary

R252 remains class-only and non-canonical. Chat 2 performs no semantic acceptance.

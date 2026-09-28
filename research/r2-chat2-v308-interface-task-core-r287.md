# Chat 2 — exact-v308 timed interface-task core R287

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

## Deterministic result

- `rs/n/b/a` -> `CLIENT_CLASS_000538` -> `TimedInterfaceTask`
- `rs/n/b/b` -> `CLIENT_CLASS_000543` -> `InterfaceTaskRegistry`
- review: `SEMREVIEW_BD054E764BBAC16C4317`
- unresolved: **0**
- member proposals: **0**

## Exact-v308 core contract

`TimedInterfaceTask` owns two timestamps: an execution interval and last-run time. Its shared execution method compares `System.currentTimeMillis()` against the last-run timestamp, invokes the subclass hook only when due, and records the new run time.

The class also owns three registries specialized by concrete task subtype. The static reset iterates every registered `InterfaceTaskRegistry` and clears it.

`InterfaceTaskRegistry` stores `int -> List<TimedInterfaceTask>` in the exact-v308 Trove map. Registration lazily allocates the list. Dispatch by integer key invokes the common interval-gated execution method for every task bound to that key.

The integer-key domain is fixed by live consumers: registrations use interface/widget ids such as 30072, 40087 and 62150-62156, and client/interface rendering paths dispatch using the active `RSInterface` id.

## Deliberate exclusions

R287 does not name `rs/n/b/a/a`, `rs/n/b/a/c`, `rs/n/b/a/d` or `rs/n/b/a/b`. Their concrete phase behavior is understood, but the precise source-level nouns for the three specialized task modes and draw callback interface remain weaker than the shared timed-task abstraction.

## Boundary

R287 is non-canonical semantic research only. No acceptance, source rewrite or source materialization is performed.

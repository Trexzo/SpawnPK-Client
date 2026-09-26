# Chat 2 — exact-v308 canvas and file operations semantics R54

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R54 is a separate non-canonical class-only semantic review batch recovering two remaining
legacy client-shell helpers.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_85873CA645C344480756`
- field/method proposals: **0**

## Stable-ID verification

Core's exact `seed_lineage()` ordering over the complete `rs/` baseline gives:

- `rs/b` -> `CLIENT_CLASS_000077`
- `rs/i` -> `CLIENT_CLASS_000295`

## `rs/b` -> `RSCanvas`

The class extends `java.awt.Canvas`, stores one wrapped `Component`, and forwards
`update(Graphics)` and `paint(Graphics)` directly to that component.

R48 `RSApplet` constructs the object with `this`, stores it as the live drawing surface,
sizes/positions it during shell setup and returns it as the active component when the
standalone R48 `RSFrame` path is not selected.

The class also owns client-specific focus handling and resizable-client size delegation.

That is exactly the RuneScape-client forwarding-canvas role conventionally described as
`RSCanvas`.

## `rs/i` -> `FileOperations`

This static utility exposes:

- pathname -> complete `byte[]` read;
- `InputStream` -> complete `byte[]` read;
- pathname + `byte[]` write;
- pathname existence check.

The direct file reader uses `FileInputStream` / `DataInputStream`; the writer creates
parent directories and writes the full payload through `FileOutputStream`.

Three static integer counters are initialized to zero. Successful pathname reads increment
the first counter; successful writes increment the second and third. The write failure
path retains the literal `Write Error:`.

The contract is the classic client `FileOperations` helper shape. Exact v308 behavior is
primary authority; the legacy name is semantic/historical recovery evidence.

## Naming boundary

These are semantic recovery names. R54 does not claim independent recovery of verbatim
original SpawnPK source identifiers.

## Acceptance boundary

Chat 2 does not promote R54. Main/Core may accept either proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_85873CA645C344480756`.

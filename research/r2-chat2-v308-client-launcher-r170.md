# Chat 2 — exact-v308 Client and Launcher R170

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R170 records the two most central exact readable class names that survive in the client
binary and were not yet represented in Chat 2 semantic review.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_FEA952C771DB52B91A41`
- confidence: **1.0** each
- field/method proposals: **0**

## Stable IDs

- `rs/Client` -> `CLIENT_CLASS_000029` -> `Client`
- `rs/gui/Launcher` -> `CLIENT_CLASS_000196` -> `Launcher`

## Client

The exact binary class is literally:

`public final class rs.Client extends rs.C`

The readable name therefore survives directly.

The class owns central live runtime state including the recovered EventBus, scene/UI/network
objects, packet-related state and the ScriptPacket dispatch context studied in R115.

`Launcher` also owns a live `rs.Client` field and accepts the Client instance in its
constructor.

R170 does not attempt to name Client's hundreds of obfuscated fields or methods.

## Launcher

The JAR manifest is direct authority:

`Main-Class: rs.gui.Launcher`

The class itself preserves the exact binary name `rs/gui/Launcher` and a public
`main(String[])` bootstrap.

The bootstrap sets process/UI/network properties and initializes startup services/logging.
Launcher instances own the live Client and desktop UI/tray components.

## Naming boundary

These are not inferred role names or reconstructed developer identifiers.

`Client` and `Launcher` are the exact readable names already present in the v308 binary
and manifest, so both proposals are confidence **1.0**.

## Acceptance boundary

R170 remains non-canonical. Main/Core may accept either proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_FEA952C771DB52B91A41`.

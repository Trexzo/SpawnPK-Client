# Chat 2 — exact-v308 ScriptPacket subsystem handlers R117

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R117 is a separate non-canonical class-only review for three R115 ScriptPacket handlers
whose target subsystems already have independently recovered semantic identities.

## Deterministic review result

- candidate classes: **3**
- resolved proposals: **3**
- unresolved: **0**
- review ID: `SEMREVIEW_55DD2BBE6CFF503C78BB`
- field/method proposals: **0**
- confidence: **0.999** each

## Stable IDs and ScriptPacket IDs

- `rs/q/a/a/a/d` -> `CLIENT_CLASS_000749`
  -> `HalloweenHungerGamesPacketHandler` — ScriptPacket **1**
- `rs/q/a/a/a/e` -> `CLIENT_CLASS_000750`
  -> `InfoBoxPacketHandler` — ScriptPacket **34**
- `rs/q/a/a/a/p` -> `CLIENT_CLASS_000761`
  -> `StatusTimerPacketHandler` — ScriptPacket **19**

## HalloweenHungerGamesPacketHandler

ScriptPacket ID 1 writes exclusively into the already-reviewed R3
`HalloweenHungerGamesOverlay`.

Exact packet-driven UI/state includes:

- match style;
- players in lobby;
- waiting/starting state;
- kills;
- survivors;
- event timers;
- active/completed flags.

Surviving text includes:

- `Match style:`
- `Players in lobby:`
- `Starting a match, please wait..`
- `Starting in:`
- `Waiting for ... players..`
- `Kills:`
- `Survivors:`

This target relationship removes any ambiguity from the handler identity.

## InfoBoxPacketHandler

ScriptPacket ID 34 drives R11 `InfoBoxManager`.

It preserves the exact literal:

`InfoBoxOverlay`

and maps incoming `def` to that default target/group name.

Its protocol can:

- remove an InfoBox by String ID;
- resolve an existing box;
- update counter values;
- update timer duration;
- remove/replace an incompatible existing box;
- construct new timer/counter/text InfoBox variants;
- attach image/title/description/group/layer metadata;
- add the resulting box to InfoBoxManager.

## StatusTimerPacketHandler

ScriptPacket ID 19 manages R11 `StatusTimer` instances.

It resolves `StatusTimerType`, finds matching entries in the Client timer list and then:

- updates duration when positive;
- removes matching timers when the incoming duration expires/clears them;
- creates a new StatusTimer when no matching entry exists.

Exact aliases include:

- `magic_sickness`
- `welfare_2x`
- `event_elixir`

Incoming names beginning with `dyn_` use a separate dynamic-timer path in the same
handler with packet-provided display/image metadata and duration.

## Naming boundary

These names are descriptive handler nouns, but their subsystem identities are not inferred
from generic packet shapes: R115 supplies exact ScriptPacket IDs and each class directly
targets a previously recovered exact-v308 subsystem.

R117 remains class-only.

## Acceptance boundary

Chat 2 does not promote R117. Main/Core may accept any subset only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_55DD2BBE6CFF503C78BB`.

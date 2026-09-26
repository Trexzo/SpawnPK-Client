# Chat 2 — exact-v308 custom-magic presentation ScriptPacket 32 R151

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R151 resolves the last deliberately unnamed ScriptPacket handler from the R115 registry.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_77BBD1D38D47DCB43557`
- field/method proposals: **0**

## Stable ID

`rs/q/a/a/a/a` -> `CLIENT_CLASS_000746`
-> `CustomMagicPresentationPacketHandler`

R115 registers this class directly as ScriptPacket **32**.

## Why this class was previously withheld

Earlier Chat 2 batches deliberately left ScriptPacket 32 unnamed.

Selector 2 was obviously magic-related because it swaps:

- `Blood barrage` vs `Infernal barrage`;
- `Blood blitz` vs `Infernal blitz`;
- their exact level-description Strings;
- corresponding `magic/on` sprites.

However, the class also writes several broad Client scalars, input-mode flags and a five-value
runtime state block. Without a common independently proven subsystem noun, naming the whole
class after only selector 2 would have violated the whole-class coherence rule.

## Exact client selector surface

The handler implements selectors **1–8**.

- **1** writes one Client scalar;
- **2** swaps the Blood/Infernal custom-magic presentation described above;
- **3** writes another Client scalar;
- **4** installs a packet-provided input prompt, clears the active input String and enables
  text-input presentation state;
- **5** reads three bytes and performs no observable state mutation;
- **6** toggles one client-side feature flag;
- **7** writes five integers into one shared runtime-presentation state block and clears its
  active flag;
- **8** toggles one interface-state flag.

The exact client therefore proves the complete structure but not, by itself, a trustworthy
English noun for every field.

## Independent application-protocol authority

The preserved SpawnPK server/application research resolves that missing boundary.

`application_protocol_r4/08_CUSTOM_MAGIC_AND_RUNTIME_STATE.md` and its R5 copy state:

> Subtype32 exposes a server-controlled presentation/state layer for custom magic.

The same authority specifically identifies:

- op2 as the Blood-vs-Infernal blitz/barrage presentation swap;
- op4 as entering client text-input mode;
- op5 as reading three bytes with no observable mutation.

Its static-boundary document separately lists:

`custom magic presentation toggles`

as exact enough to implement client-side while keeping:

`custom magic combat effects`

server-owned.

That distinction is important: R151 names the client presentation/state protocol, not custom
magic combat logic.

## Producer corroboration

The preserved `ApplicationUiService` exposes subtype 32 only through:

- `customMagicScalarCT`;
- `customMagicInfernalMode`;
- `customMagicScalarDX`;
- `customMagicPrompt`;
- `customMagicNoop5`;
- `customMagicFlag6`;
- `customMagicFive`;
- `customMagicFlag8`.

This producer vocabulary matches all eight exact client selectors.

## Naming boundary

`CustomMagicPresentationPacketHandler` is descriptive at **0.999**.

The name intentionally uses **Presentation** rather than a combat/service noun. Exact-v308
bytecode supplies the complete selector behavior; preserved application-protocol authority
supplies the whole-class domain boundary that earlier Chat 2 reviews lacked.

The name is not claimed as a surviving original client source identifier.

## ScriptPacket frontier status

With R151, every ScriptPacket handler in the exact R115 ID **1–43** registry now has either:

- a reviewed semantic identity of its own; or
- an identity through its already-reviewed owning subsystem/handler batch.

There are no deliberately unnamed R115 ScriptPacket handlers left.

## Acceptance boundary

Chat 2 does not promote R151. Main/Core may accept this proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_77BBD1D38D47DCB43557`.

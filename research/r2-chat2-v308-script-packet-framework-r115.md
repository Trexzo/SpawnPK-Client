# Chat 2 — exact-v308 ScriptPacket framework R115

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R115 is a separate non-canonical class-only review for the exact ScriptPacket handler
framework invoked directly by the v308 Client packet loop.

## Deterministic review result

- candidate classes: **2**
- resolved proposals: **2**
- unresolved: **0**
- review ID: `SEMREVIEW_6A2949D5AE0162BAD9B4`
- field/method proposals: **0**
- confidence: **0.999** each

## Stable IDs

- `rs/q/a/a/a` -> `CLIENT_CLASS_000745` -> `ScriptPacketHandler`
- `rs/q/a/a/b` -> `CLIENT_CLASS_000762` -> `ScriptPacketDispatcher`

## ScriptPacketHandler

The abstract base implements `com.google.inject.Module`.

Each instance owns injected:

- Guice Injector;
- exact packet buffer `rs/x/e`;
- live Client.

Its abstract no-argument method is the per-packet handling entry point.

The base also provides shared packet-buffer helpers for:

- integer reads;
- long reads;
- String reads;
- scoped cursor/reset reads.

Concrete subclasses include exact UI/event update handlers such as the updater siblings
used by the R111-R114 overlay family.

## ScriptPacketDispatcher

The class preserves exact framework diagnostics:

- `ScriptPacket ID <id> already in use!`
- `Could not find ScriptPacket ID <id>!`

Initialization registers IDs **1 through 43** into:

`Map<Integer, ScriptPacketHandler>`

Some registrations use direct handler classes while others use live singleton handler
instances exposed by their owning UI/game subsystem.

For each handler the dispatcher:

1. reflectively invokes the no-argument constructor;
2. creates a Guice child injector;
3. binds the handler class to that exact instance;
4. installs the instance as a Module;
5. stores the child Injector on the handler;
6. inserts the handler into the ID map;
7. rejects duplicate IDs.

## Exact Client dispatch

Client initialization calls the ScriptPacket registry initialization method.

The live packet loop has a dedicated packet branch for opcode **250**.

That branch:

1. reads one integer from the current `rs/x/e` packet buffer;
2. treats it as the ScriptPacket ID;
3. calls `ScriptPacketDispatcher(Client, buffer, id)`.

The dispatcher looks up the handler. If absent, it prints the exact missing-ID diagnostic.
If present, it installs the current buffer and Client on the handler and invokes the
handler entry point.

This fixes the framework role independently of the obfuscated package names.

## Naming boundary

The exact noun `ScriptPacket` survives directly in v308 diagnostics.

`Handler` and `Dispatcher` are descriptive role nouns rather than claims that original
source identifiers survive, but the protocol family/domain is exact. Confidence is 0.999.

R115 remains class-only and does not assign names to the handler methods or individual
ScriptPacket IDs.

## Acceptance boundary

Chat 2 does not promote R115. Main/Core may accept either proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_6A2949D5AE0162BAD9B4`.

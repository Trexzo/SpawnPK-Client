# Chat 2 — exact-v308 client shortcut key handler R197

Exact client authority:

`854f26ff9f134b0317572e7ac1688e6f40a231d5a4c66f8db5d655b7f45ce7c6`

R197 is a separate non-canonical class-only review for the exact client keyboard shortcut
dispatcher.

## Deterministic review result

- candidate classes: **1**
- resolved proposals: **1**
- unresolved: **0**
- review ID: `SEMREVIEW_4C8C7F5FC8192D96005A`
- field/method proposals: **0**

## Stable ID

`rs/h/d` -> `CLIENT_CLASS_000292` -> `ClientShortcutKeyHandler`

The stable ID is the deterministic exact-v308 R1 baseline identity.

## Exact keyboard surface

The class stores the live `Client` instance and exposes two methods that receive
`java.awt.event.KeyEvent`.

The first path dispatches exact keyboard shortcuts to textual client commands:

- `::tm`;
- `::home`;
- `::opentp`;
- `::loot`;
- `::bank`;
- `::clogs`;
- `::e`.

Those commands are not written directly as arbitrary chat text. The class queues them and
emits them through the exact command-packet path using opcode **103**.

## Exact widget shortcuts

The second KeyEvent path handles shortcuts while interface root **23000** is open.

It can:

- invoke the exact bank interface helper;
- send widget-click opcode **185** to component **38976**;
- send widget-click opcode **185** to component **26012**;
- send widget-click opcode **185** to component **26016**;
- send widget-click opcode **185** to component **5294**;
- send widget-click opcode **185** to component **38980**.

This is the same exact client-side widget-click transport used elsewhere in the recovered
interface stack.

## Guard behavior

Shortcut dispatch is gated by exact client state:

- current root interface;
- whether another interface is open;
- login/client state;
- recent-input timing/state;
- a local enabled/disabled flag.

The class therefore owns both shortcut recognition and shortcut eligibility rather than
merely wrapping the packet writer.

## Naming boundary

`ClientShortcutKeyHandler` is **0.999**.

The name intentionally avoids claiming that the class is the global AWT key-listener
manager. R175 already recovers the broader `ClientKeyListener` / `KeyListenerManager`
surface. This class is specifically the SpawnPK client-command/widget shortcut layer
triggered from KeyEvent input.

No original developer identifier is claimed.

## Acceptance boundary

Chat 2 does not promote R197. Main/Core may accept this proposal only through an explicit
`semantic_acceptance_spec` bound to `SEMREVIEW_4C8C7F5FC8192D96005A`.
